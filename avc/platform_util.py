from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AGENTS = ("cursor", "claude", "codex")
AGENT_LABELS = {
    "cursor": "Cursor",
    "claude": "Claude",
    "codex": "Codex",
}


def install_root() -> Path:
    return Path(__file__).resolve().parent.parent


def os_kind() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def path_example() -> str:
    if os_kind() == "windows":
        return r"C:\Users\你\Desktop\我的小說"
    if os_kind() == "mac":
        return "/Users/你/Desktop/我的小說"
    return "/home/你/我的小說"


def python_invocation() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    exe = Path(sys.executable)
    name = exe.name.lower()
    if os_kind() == "windows":
        if "python" in name:
            return [str(exe)]
        return ["py", "-3"]
    return [str(exe)] if exe.exists() else ["python3"]


def python_invocation_text() -> str:
    parts = python_invocation()
    return " ".join(quote_cmd(p) for p in parts)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def avc_command_text() -> str:
    """Portable way to refer to the tool in docs / SKILL files.

    Never bake in a machine-specific absolute path (it would contain this
    computer's user name), because the project is shared with other people whose
    paths differ. Inside a tracked folder the relative launcher
    (``.avc/avc.cmd`` or ``.avc/avc.py``) is always preferred; this is only the
    generic fallback form.
    """
    if is_frozen():
        return "avc.exe"
    return "python -m avc"


def quote_cmd(part: str) -> str:
    if os_kind() == "windows" and (" " in part or "&" in part):
        return f'"{part}"'
    if " " in part:
        return f'"{part}"'
    return part


def enable_utf8() -> None:
    if os_kind() != "windows":
        return
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def pick_folder(prompt: str = "選擇要記錄的資料夾") -> str | None:
    kind = os_kind()
    if kind == "mac":
        script = f'POSIX path of (choose folder with prompt "{prompt}")'
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        return proc.stdout.strip().rstrip("/")
    if kind == "windows":
        # Launched from a background/console process (or the packaged .exe), a bare
        # FolderBrowserDialog opens *behind* the browser window and never gets focus,
        # so the button looks dead. Own it with a hidden TopMost form so it comes to
        # the front, and activate that form right before showing the dialog.
        ps = f"""
Add-Type -AssemblyName System.Windows.Forms
[void][System.Windows.Forms.Application]::EnableVisualStyles()
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.StartPosition = 'CenterScreen'
$owner.Opacity = 0
$owner.Show()
$owner.Activate()
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '{prompt}'
$dialog.ShowNewFolderButton = $true
$result = $dialog.ShowDialog($owner)
$owner.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.SelectedPath
}}
"""
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(
            ["powershell", "-STA", "-NoProfile", "-Command", ps],
            capture_output=True,
            creationflags=creationflags,
        )
        if proc.returncode != 0:
            return None
        text = proc.stdout.decode("utf-8", errors="replace").strip()
        return text or None
    for cmd in (
        ["zenity", "--file-selection", "--directory", "--title", prompt],
        ["kdialog", "--getexistingdirectory", ".", prompt],
    ):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            continue
        if proc.returncode == 0:
            return proc.stdout.strip() or None
        return None
    return _tk_folder(prompt)


def _tk_folder(prompt: str) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askdirectory(title=prompt)
    root.destroy()
    return chosen or None


def _win_app_path(exe_name: str) -> Path | None:
    """Look up an executable via the Windows 'App Paths' registry key."""
    try:
        import winreg
    except ImportError:
        return None
    key = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, key) as k:
                value, _ = winreg.QueryValueEx(k, None)
        except OSError:
            continue
        if value:
            p = Path(value.strip('"'))
            if p.exists():
                return p
    return None


def _find_windows_browser(exe_name: str, subdirs: list[str]) -> Path | None:
    found = _win_app_path(exe_name)
    if found:
        return found
    roots = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    for root in roots:
        if not root:
            continue
        for sub in subdirs:
            candidate = Path(root) / sub / exe_name
            if candidate.exists():
                return candidate
    return None


def open_url(url: str) -> None:
    """Open the app in a browser. On Windows prefer Chrome, then Edge, then the
    system default; elsewhere use the default browser."""
    if os_kind() == "windows":
        preferences = [
            ("chrome.exe", [r"Google\Chrome\Application"]),
            ("msedge.exe", [r"Microsoft\Edge\Application"]),
        ]
        for exe_name, subdirs in preferences:
            exe = _find_windows_browser(exe_name, subdirs)
            if exe:
                try:
                    subprocess.Popen([str(exe), url])
                    return
                except OSError:
                    continue
    import webbrowser

    webbrowser.open(url)


def platform_info() -> dict:
    return {
        "os": os_kind(),
        "python": python_invocation_text(),
        "path_example": path_example(),
        "install_root": str(install_root()),
        "agents": [{"id": k, "label": AGENT_LABELS[k]} for k in AGENTS],
    }
