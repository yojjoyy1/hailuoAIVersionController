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
        ps = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '{prompt}'
$dialog.ShowNewFolderButton = $true
[void][System.Windows.Forms.Application]::EnableVisualStyles()
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.SelectedPath
}}
"""
        proc = subprocess.run(
            ["powershell", "-STA", "-NoProfile", "-Command", ps],
            capture_output=True,
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


def platform_info() -> dict:
    return {
        "os": os_kind(),
        "python": python_invocation_text(),
        "path_example": path_example(),
        "install_root": str(install_root()),
        "agents": [{"id": k, "label": AGENT_LABELS[k]} for k in AGENTS],
    }
