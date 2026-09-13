from __future__ import annotations

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


def write_bootstrap(project_root: Path) -> None:
    avc_dir = project_root / ".avc"
    avc_dir.mkdir(parents=True, exist_ok=True)
    # When frozen, install_root() is a throwaway PyInstaller temp dir, so we must
    # not bake it into the fallback script; the .exe (referenced by avc.cmd) is
    # the real engine. From source we point Python at the install directory.
    if is_frozen():
        path_line = ""
    else:
        root = str(install_root()).replace("\\", "\\\\")
        path_line = f'sys.path.insert(0, r"{root}")\n'
    (avc_dir / "avc.py").write_text(
        f'''# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

{path_line}project = Path(__file__).resolve().parent.parent
os.chdir(os.environ.get("AVC_CWD", str(project)))

from avc.cli import main

if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
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
