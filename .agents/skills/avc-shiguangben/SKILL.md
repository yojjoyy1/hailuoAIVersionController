---
name: avc-shiguangben
description: Records AI collaboration sessions, folder file changes, tagged snapshots, diffs, and restores using the local 時光本 (avc) CLI and SQLite. Use when starting or ending an AI work session, saving a labeled checkpoint, comparing or restoring folder states, or when the user mentions 時光本, 版本控制, 紀錄, 標籤, 還原, or avc. Works with Cursor, Claude Code, and Codex on macOS and Windows.
---

# 時光本（AI 協作版本控制）

給不懂 Git 的人用的本地版本控制。檔案狀態、對話 session、標籤都寫進 SQLite，**只能透過 CLI 讀寫資料庫**，不要自己改 `.avc/` 或寫記事本當正式紀錄。

目前這個專案設定的 AI Agent：**Codex**
你正在 Codex。`--source` 填目前 session 名稱。專案 skill 在 `.agents/skills/avc-shiguangben/`。

在**被記錄的資料夾**執行（該資料夾裡會有 `.avc/avc.py`）：

```text
python3 .avc/avc.py -p . status
```

Windows 則用：`py -3 .avc\avc.py -p . status`

若專案裡還沒有 `.avc/avc.py`，把時光本安裝目錄加入模組路徑後執行（安裝目錄：`/Users/linxinyi/Desktop/AI版本控制工具`）：

```text
/Library/Developer/CommandLineTools/usr/bin/python3 -m avc -p <專案資料夾> status
```

輸出皆為 JSON。stderr 若為 `{"error": ...}`，先處理錯誤。

Windows 請用 PowerShell 或 Windows Terminal；指令是 `py -3` 或 `python`，不一定有 `python3`。
Mac / Linux 優先 `python3`。路徑含空白要加引號。

## 何時一定要做

開始改這個資料夾的檔案之前：

1. 確認已 `init`（有 `.avc/avc.sqlite`）。沒有就 `init --name "..."`，`--agent codex`。
2. `session start --title "..." --agent codex`，`--source` 填目前對話名稱。
3. 用 `note` 寫入使用者這次的請求（可摘要）。
4. 工作結束或使用者要「記住」：`status` → `save --label --note`。
5. 對話告一段落：`session end`。

使用者要回頭、切換、比對、還原時，用 `list` / `diff` / `restore`，不要改用 git（除非使用者明確要 git）。

## 指令

把 `AVC` 換成 `.avc/avc.py`（在專案內）或 `/Library/Developer/CommandLineTools/usr/bin/python3 -m avc`：

```text
AVC init --name "專案名稱" --agent codex
AVC status
AVC session start --title "改封面" --source "對話名稱" --agent codex
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
