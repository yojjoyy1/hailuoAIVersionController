from __future__ import annotations

import json
from pathlib import Path

import sys

from avc.platform_util import (
    AGENT_LABELS,
    AGENTS,
    avc_command_text,
    install_root,
    is_frozen,
    os_kind,
    python_invocation_text,
)

SKILL_NAME = "avc-shiguangben"

PROJECT_SKILL_DIRS = {
    "cursor": [".cursor/skills/avc-shiguangben"],
    "claude": [".claude/skills/avc-shiguangben"],
    "codex": [".agents/skills/avc-shiguangben"],
}

USER_SKILL_DIRS = {
    "cursor": [Path.home() / ".cursor" / "skills" / SKILL_NAME],
    "claude": [Path.home() / ".claude" / "skills" / SKILL_NAME],
    "codex": [
        Path.home() / ".agents" / "skills" / SKILL_NAME,
        Path.home() / ".codex" / "skills" / SKILL_NAME,
    ],
}


def render_skill(agent: str = "cursor") -> str:
    agent = normalize_agent(agent)
    label = AGENT_LABELS[agent]
    avc_cmd = avc_command_text()
    extra = {
        "cursor": "你正在 Cursor。`--source` 填目前聊天標題。專案 skill 在 `.cursor/skills/avc-shiguangben/`。",
        "claude": "你正在 Claude Code。`--source` 填目前對話名稱。專案 skill 在 `.claude/skills/avc-shiguangben/`，可用 `/avc-shiguangben`。",
        "codex": "你正在 Codex。`--source` 填目前 session 名稱。專案 skill 在 `.agents/skills/avc-shiguangben/`。",
    }[agent]
    unix_run = "python3 .avc/avc.py"
    win_run = ".avc\\avc.cmd"
    if os_kind() == "windows":
        preferred = win_run
        other = unix_run
        other_os = "Mac / Linux"
    else:
        preferred = unix_run
        other = win_run
        other_os = "Windows"
    return f"""---
name: avc-shiguangben
description: Local version control (時光本 / avc) for a tracked folder. IMPORTANT — use this skill PROACTIVELY and AUTOMATICALLY whenever you are about to create, modify, rename, or delete ANY file inside a folder tracked by 時光本 (its root has a .avc/ folder or .avc/avc.sqlite): start a conversation session BEFORE editing and save AFTER, even if the user never mentions 時光本. Also use it to start or end a work session, save a labeled snapshot, diff or restore folder states, or when the user mentions 時光本, 版本控制, 紀錄, 標籤, 還原, or avc. Works with Cursor, Claude Code, and Codex on Windows and macOS.
---

# 時光本（AI 協作版本控制）

給不懂 Git 的人用的本地版本控制。檔案狀態、對話 session、標籤都寫進 SQLite，**只能透過 CLI 讀寫資料庫**，不要自己改 `.avc/` 或寫記事本當正式紀錄。

目前這個專案設定的 AI Agent：**{label}**
{extra}

> ⚠️ **核心規則**：只要這個資料夾有被時光本記錄（根目錄有 `.avc/`），你在**動任何檔案（新增／修改／改名／刪除）之前**，就要先確保有一個進行中的對話 session（沒有就先 `session start`），做完後 `save`，**即使使用者沒有提到時光本、只說「幫我改 X／建立 Y」也一樣**。這樣使用者網頁才會把你的改動自動歸到「對話」與「紀錄時間軸」；沒開 session 就改檔，會被當成人工改動、只出現在「現在的改動」。詳見下方「何時一定要做」。

在**被記錄的資料夾**執行（該資料夾裡會有 `.avc/avc.py`）：

```text
{preferred} -p . status
```

{other_os} 則用：`{other} -p . status`

若專案裡還沒有那個啟動檔，就用「時光本」主程式（**路徑請換成你自己電腦上的位置，不要沿用別人的使用者名稱**）：

```text
# 打包版：把 <你的時光本資料夾> 換成實際路徑
<你的時光本資料夾>\\dist\\avc.exe -p <專案資料夾> status
# 原始碼版：先切到你的時光本資料夾再執行
python -m avc -p <專案資料夾> status
```

輸出皆為 JSON。stderr 若為 `{{"error": ...}}`，先處理錯誤。

Windows 用 PowerShell 或 Windows Terminal 執行 `.avc\\avc.cmd`：它會自動找到時光本主程式（打包好的 .exe）或 `python`，不需要 `py`。
Mac / Linux 優先 `python3`。路徑含空白要加引號。

## 何時一定要做

**任何會改到這個資料夾檔案的任務都適用**（新增、修改、改名、刪除；即使使用者只說「幫我改 X／建立 Y」而沒提到時光本）。動手改檔**之前**：

1. 確認已 `init`（有 `.avc/avc.sqlite`）。沒有就 `init --name "..."`，`--agent {agent}`。
2. 先 `status`，看回傳的 `active_session_id`：**若是 null（沒有進行中的對話），一定要先** `session start --title "<這次要做的事>" --source "<目前對話名稱>" --agent {agent}`。
3. 用 `note --role user` 寫入使用者這次的請求（可摘要）。
4. 改完檔、或使用者說「記住」：`status` → `save --label "<看得懂的名字>" --note "<改了什麼>"`。
5. 這輪工作結束：`session end`。

沒有先開 session 就改檔 → 使用者網頁會當成人工改動、只顯示在「現在的改動」；有開 session 才會自動同步到「對話」與「紀錄時間軸」。

使用者要回頭、切換、比對、還原時，用 `list` / `diff` / `restore`，不要改用 git（除非使用者明確要 git）。

## 指令

把 `AVC` 換成 `{preferred}`（在專案內，建議用這個）或主程式 `{avc_cmd}`（在你自己的時光本資料夾）：

```text
AVC init --name "專案名稱" --agent {agent}
AVC status
AVC session start --title "改封面" --source "對話名稱" --agent {agent}
AVC session end
AVC note --role user --content "請把封面改成藍色"
AVC note --role assistant --content "已改封面配色"
AVC session changes <session_id> --summary
AVC save --label "藍色封面" --note "封面從紅改藍"
AVC relabel <id> --label "我看得懂的名字"
AVC list
AVC show <id> --files
AVC diff <較早id> <較新id>
AVC diff <id>
AVC restore <id>
AVC restore <id> --force
AVC clear --yes
```

`switch` 等於 `restore`。人類介面：`AVC web`（只聽 127.0.0.1）。

## 用詞（對使用者說話時）

不要說 commit / checkout / branch / repo / diff；改說記住、標籤、切換到那一次、資料夾、這兩次差在哪。

## 還原規則

有未紀錄改動時，先問要記住還是放棄後 `--force`。Windows 上若檔案正被 Word/Excel 打開，還原會失敗，請使用者先關閉再試。任何已 save 的紀錄都可以互相比對、互相切換。

## 不要做的事

- 不要手改 SQLite，不要把狀態寫進 .md 當正式紀錄。
- 不要把 `.avc/` 資料庫內容貼進對話。需要時用 `status`、`diff --summary`、`show`。
- 除非使用者明確說要清空紀錄，否則不要執行 `clear`。
"""



# ---------------------------------------------------------------------------
# 常駐指令檔（always-loaded memory）
#
# skill 是「按需觸發」的：Claude Code / Codex 平常只載入 skill 的
# name+description，模型要自己決定去叫它才會執行內文。像「動檔前一定要先開
# session」這種每次都要做的規則，交給按需 skill 並不可靠（Cursor 之所以穩，是
# 因為它把 skill 內容較積極地塞進每一輪 context）。這裡改寫入各 agent 的「常駐
# 指令檔」——Claude 用 CLAUDE.md、Codex 用 AGENTS.md——它們每次開 session 都一定
# 被載入，等於複製 Cursor「每輪都看得到規則」的效果。
# ---------------------------------------------------------------------------

PROJECT_MEMORY_FILES = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
}

MEMORY_BEGIN = "<!-- avc-shiguangben:begin (自動產生，勿手改此區塊) -->"
MEMORY_END = "<!-- avc-shiguangben:end -->"

_MEMORY_SKILL_PATH = {
    "cursor": ".cursor/skills/avc-shiguangben/SKILL.md",
    "claude": ".claude/skills/avc-shiguangben/SKILL.md",
    "codex": ".agents/skills/avc-shiguangben/SKILL.md",
}


def render_project_memory(agent: str) -> str:
    agent = normalize_agent(agent)
    skill_path = _MEMORY_SKILL_PATH[agent]
    run = ".avc\\avc.cmd" if os_kind() == "windows" else "python3 .avc/avc.py"
    return f"""# 時光本（avc）自動記錄規則 —— 每次都要遵守

這個資料夾由「時光本」記錄版本。**在動任何檔案（新增／修改／改名／刪除）之前**，一定要先確保有一個進行中的對話 session，做完後 `save`——**即使使用者沒提到時光本、只說「幫我改 X／建立 Y」也一樣**。沒有先開 session 就改檔，改動會被當成人工改動，只出現在「現在的改動」，不會歸到「對話／紀錄時間軸」。

流程（Mac / Linux 用 `python3 .avc/avc.py`；Windows 用 `.avc\\avc.cmd`）：

1. `{run} -p . status` —— 看回傳的 `active_session_id`。
2. 若為 null：`{run} -p . session start --title "<這次要做的事>" --source "<目前對話名稱>" --agent {agent}`。
3. `{run} -p . note --role user --content "<使用者這次的請求>"`。
4. 改完檔、或使用者說「記住」：`{run} -p . save --label "<看得懂的名字>" --note "<改了什麼>"`。
5. 這輪工作結束：`{run} -p . session end`。

完整指令與還原／比對規則見 skill：`{skill_path}`。對使用者說話時用「記住／標籤／切換到那一次／資料夾」，不要說 commit／branch／diff。"""


def _upsert_memory_block(path: Path, body: str) -> None:
    block = f"{MEMORY_BEGIN}\n{body}\n{MEMORY_END}\n"
    try:
        existing = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        existing = None
    except (OSError, UnicodeDecodeError):
        return
    if existing is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block, encoding="utf-8")
        return
    if MEMORY_BEGIN in existing and MEMORY_END in existing:
        start = existing.index(MEMORY_BEGIN)
        end = existing.index(MEMORY_END) + len(MEMORY_END)
        new_text = existing[:start] + block.rstrip("\n") + existing[end:]
        if new_text != existing:
            path.write_text(new_text, encoding="utf-8")
        return
    sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    path.write_text(existing + sep + block, encoding="utf-8")


def _strip_memory_block(path: Path) -> None:
    """移除我們寫入的區塊，保留使用者自己的內容；若整個檔案原本只有我們的區塊
    （代表是我們建立的），就把檔案刪掉，不留空檔。"""
    try:
        existing = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    if MEMORY_BEGIN not in existing or MEMORY_END not in existing:
        return
    start = existing.index(MEMORY_BEGIN)
    end = existing.index(MEMORY_END) + len(MEMORY_END)
    tail = existing[end:]
    if tail.startswith("\n"):
        tail = tail[1:]
    remainder = existing[:start] + tail
    if remainder.strip() == "":
        try:
            path.unlink()
        except OSError:
            pass
        return
    path.write_text(remainder, encoding="utf-8")



# ---------------------------------------------------------------------------
# Claude Code hooks（.claude/settings.json）
#
# 這是真正「不靠模型記得」的自動記錄：改檔就一定觸發 avc。只在 agent = claude 時
# 安裝，切換到別的 agent 會移除。用 command 內含的 `_autohook` 字樣辨識我們寫的
# 項目，重裝時只換掉自己的、保留使用者原有的 hooks；若 settings.json 無法解析，
# 一律不動，避免破壞使用者設定。
# ---------------------------------------------------------------------------

CLAUDE_SETTINGS_REL = ".claude/settings.json"
_HOOK_MARKER = "_autohook"


def _hook_command(project_root: Path, event: str) -> str:
    root = project_root.resolve()
    if os_kind() == "windows":
        launcher = str(root / ".avc" / "avc.cmd")
        return f'"{launcher}" -p "{root}" _autohook {event} >nul 2>&1'
    launcher = str(root / ".avc" / "avc")
    return f'"{launcher}" -p "{root}" _autohook {event} >/dev/null 2>&1'


def _load_settings(path: Path):
    """回傳 (data, ok)。ok=False 代表檔案存在但無法安全解析，呼叫端應完全不動它。"""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, True
    except (OSError, UnicodeDecodeError):
        return None, False
    if not text.strip():
        return {}, True
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, False
    if not isinstance(data, dict):
        return None, False
    return data, True


def _strip_our_hooks(hooks: dict) -> None:
    for event in list(hooks.keys()):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for g in groups:
            if not isinstance(g, dict):
                kept_groups.append(g)
                continue
            hlist = g.get("hooks")
            if isinstance(hlist, list):
                filtered = [
                    h for h in hlist
                    if not (isinstance(h, dict) and _HOOK_MARKER in str(h.get("command", "")))
                ]
                if not filtered:
                    continue  # 整組都是我們的 -> 丟掉
                g["hooks"] = filtered
            kept_groups.append(g)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]


def install_project_claude_hooks(project_root: Path) -> list[str]:
    path = project_root / CLAUDE_SETTINGS_REL
    data, ok = _load_settings(path)
    if not ok or data is None:
        return []  # 使用者的 settings.json 無法解析，保持不動
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
    _strip_our_hooks(hooks)

    def group(event: str) -> dict:
        return {"hooks": [{"type": "command", "command": _hook_command(project_root, event)}]}

    hooks.setdefault("SessionStart", []).append(group("session-begin"))
    hooks.setdefault("Stop", []).append(group("autosave"))
    hooks.setdefault("SessionEnd", []).append(group("session-finish"))
    data["hooks"] = hooks
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return []
    return [str(path)]


def remove_project_claude_hooks(project_root: Path) -> None:
    path = project_root / CLAUDE_SETTINGS_REL
    data, ok = _load_settings(path)
    if not ok or not data:
        return
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return
    before = json.dumps(hooks, ensure_ascii=False, sort_keys=True)
    _strip_our_hooks(hooks)
    after = json.dumps(hooks, ensure_ascii=False, sort_keys=True)
    if before == after:
        return  # 沒有我們的項目，不用寫
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass



def sync_project_memory(project_root: Path, agent: str) -> list[str]:
    """把選定 agent 的常駐指令檔寫好（或更新我們的區塊），並清掉其他 agent 常駐
    指令檔裡我們的舊區塊，避免切換 agent 後留下互相衝突的常駐規則。"""
    agent = normalize_agent(agent)
    written: list[str] = []
    fname = PROJECT_MEMORY_FILES.get(agent)
    if fname:
        dest = project_root / fname
        try:
            _upsert_memory_block(dest, render_project_memory(agent))
            written.append(str(dest))
        except OSError:
            pass
    for other, other_name in PROJECT_MEMORY_FILES.items():
        if other == agent:
            continue
        _strip_memory_block(project_root / other_name)
    # Claude Code hooks：只有 claude 裝，其他 agent 移除
    if agent == "claude":
        written += install_project_claude_hooks(project_root)
    else:
        remove_project_claude_hooks(project_root)
    return written


def normalize_agent(agent: str | None) -> str:
    value = (agent or "cursor").strip().lower()
    if value not in AGENTS:
        raise ValueError(f"agent 只能是 cursor、claude 或 codex，收到：{agent}")
    return value


def write_skill(dir_path: Path, agent: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "SKILL.md").write_text(render_skill(agent), encoding="utf-8")


def install_project_skill(project_root: Path, agent: str) -> list[str]:
    agent = normalize_agent(agent)
    written = []
    for rel in PROJECT_SKILL_DIRS[agent]:
        dest = project_root / rel
        write_skill(dest, agent)
        written.append(str(dest / "SKILL.md"))
    return written


def install_user_skill(agent: str) -> list[str]:
    agent = normalize_agent(agent)
    written = []
    for dest in USER_SKILL_DIRS[agent]:
        try:
            write_skill(dest, agent)
            written.append(str(dest / "SKILL.md"))
        except OSError:
            continue
    return written


def refresh_existing_user_skills() -> list[str]:
    """Rewrite any already-installed user-level SKILL.md so stale instructions
    (e.g. an old `py -3` command that fails when there's no `py` launcher) get
    updated to match the current build. Only touches skills that already exist,
    so we never create clutter for agents the user doesn't use."""
    written = []
    for agent, dirs in USER_SKILL_DIRS.items():
        for dest in dirs:
            if not (dest / "SKILL.md").exists():
                continue
            try:
                write_skill(dest, agent)
                written.append(str(dest / "SKILL.md"))
            except OSError:
                continue
    return written


def install_tool_repo_skills() -> None:
    # No source tree to write into when running as a packaged .exe.
    if is_frozen():
        return
    root = install_root()
    for agent, rels in PROJECT_SKILL_DIRS.items():
        for rel in rels:
            write_skill(root / rel, agent)


# `.avc/avc.py` 的內容範本。被追蹤的專案裡沒有 avc 套件本體（本體在時光本安裝
# 資料夾，例如 AI版空），所以這支啟動檔要自己找到那個資料夾。這裡用多層自動偵測，
# 正常情況免設定，搬家或走連線/Cowork 也能自動找到。寫檔時 %%BAKED%% 會換成安裝
# 當下記錄的絕對路徑。
_AVC_PY_TEMPLATE = r'''# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

_BAKED = r"%%BAKED%%"


def _locate_avc_home():
    # 1) 已經能 import avc（已安裝，或已在 PYTHONPATH）
    try:
        import avc  # noqa: F401
        return "__importable__"
    except Exception:
        pass
    candidates = []
    # 2) 環境變數 AVC_HOME（最優先的手動覆蓋）
    env = os.environ.get("AVC_HOME")
    if env:
        candidates.append(Path(env))
    # 3) 安裝當下記錄的絕對路徑
    if _BAKED:
        candidates.append(Path(_BAKED))
    # 4) 常見位置
    home = Path.home()
    for name in ("AI版空", "時光本"):
        candidates.append(home / name)
        candidates.append(home / "Desktop" / name)
        candidates.append(home / "桌面" / name)
    # 5) 連線 / Cowork：資料夾常被掛在 ~/mnt/<名稱> 下，逐一掃描
    mnt = home / "mnt"
    if mnt.is_dir():
        try:
            candidates += sorted(mnt.iterdir())
        except OSError:
            pass
    for c in candidates:
        try:
            if (c / "avc" / "__init__.py").exists():
                return str(c)
        except OSError:
            continue
    return None


_home = _locate_avc_home()
if _home is None:
    sys.stderr.write('{"error": "找不到時光本主程式。請設定環境變數 AVC_HOME 指向時光本資料夾（例如 AI版空）。"}\n')
    sys.exit(1)
if _home != "__importable__":
    sys.path.insert(0, _home)

project = Path(__file__).resolve().parent.parent
os.chdir(os.environ.get("AVC_CWD", str(project)))

from avc.cli import main

if __name__ == "__main__":
    main()
'''


def write_bootstrap(project_root: Path) -> None:
    avc_dir = project_root / ".avc"
    avc_dir.mkdir(parents=True, exist_ok=True)
    # When frozen, install_root() is a throwaway PyInstaller temp dir, so we must
    # not bake it into the fallback script; the .exe (referenced by avc.cmd) is
    # the real engine. From source we point Python at the install directory.
    if is_frozen():
        baked = ""
    else:
        baked = str(install_root()).replace("\\", "\\\\")
    (avc_dir / "avc.py").write_text(
        _AVC_PY_TEMPLATE.replace("%%BAKED%%", baked), encoding="utf-8"
    )
    # When running from a packaged .exe, point the launcher straight at it so
    # the machine needs no Python at all. After cd to the project folder the exe
    # uses the current directory as the target project.
    exe_block = ""
    if is_frozen() and os_kind() == "windows":
        exe = str(Path(sys.executable).resolve())
        exe_block = (
            f'if exist "{exe}" (\r\n'
            f'  "{exe}" %*\r\n'
            "  exit /b %ERRORLEVEL%\r\n"
            ")\r\n"
        )
    (avc_dir / "avc.cmd").write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "cd /d \"%~dp0..\"\r\n"
        + exe_block
        + "where py >nul 2>nul && py -3 \"%~dp0avc.py\" %* && exit /b %ERRORLEVEL%\r\n"
        "where python >nul 2>nul && python \"%~dp0avc.py\" %* && exit /b %ERRORLEVEL%\r\n"
        "where python3 >nul 2>nul && python3 \"%~dp0avc.py\" %* && exit /b %ERRORLEVEL%\r\n"
        "echo 找不到時光本主程式，也找不到 Python。\r\n"
        "exit /b 1\r\n",
        encoding="utf-8",
    )
    unix = avc_dir / "avc"
    unix.write_text(
        "#!/bin/sh\n"
        'cd "$(dirname "$0")/.."\n'
        'if command -v python3 >/dev/null 2>&1; then exec python3 ".avc/avc.py" "$@"; fi\n'
        'if command -v python >/dev/null 2>&1; then exec python ".avc/avc.py" "$@"; fi\n'
        'echo "找不到 Python 3" >&2\n'
        "exit 1\n",
        encoding="utf-8",
    )
    try:
        unix.chmod(unix.stat().st_mode | 0o111)
    except OSError:
        pass
