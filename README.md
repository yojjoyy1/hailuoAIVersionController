# 時光本

給**不懂程式的人**跟 AI 一起改資料夾時用的本地版本控制。支援 **Mac 與 Windows**，AI Agent 可選 **Cursor / Claude / Codex**。

## 你怎麼用（網頁）

- **Mac**：雙擊 `開啟時光本.command`

  從 GitHub 下載的檔案，第一次開可能出現黃色警告（Apple 無法驗證）。請按「完成」，不要丟到垃圾桶；到「系統設定 → 隱私權與安全性」最下面按「仍要打開」，再雙擊一次。也可看資料夾裡的 `出現黃色警告時請看這裡.txt`。
- **Windows**：雙擊 `開啟時光本.bat`（需已安裝 Python 3，並勾選 Add python.exe to PATH）

瀏覽器會打開 `http://127.0.0.1:8765`。

1. 按「開始記錄」→ **瀏覽** 選資料夾（不必手打路徑）
2. 選這個資料夾主要用哪一種 AI：**Cursor、Claude 或 Codex**（會寫入對應 SKILL）
3. 跟 AI 工作時可按「開始對話紀錄」
4. 告一段落按「記住這次改動」
5. 時間軸可回頭看、互相比對、切換回去

只在你這台電腦、只聽本機網址。

## AI 怎麼用

選好 Agent 後，會在資料夾寫入兩種東西：

**1. SKILL（技能，按需觸發）**

| Agent | SKILL 位置 |
| --- | --- |
| Cursor | `.cursor/skills/avc-shiguangben/` |
| Claude | `.claude/skills/avc-shiguangben/` |
| Codex | `.agents/skills/avc-shiguangben/` |

**2. 常駐指令檔（每次開始對話都會被載入）**

| Agent | 常駐指令檔 |
| --- | --- |
| Cursor | （用 SKILL 即可，不另外寫） |
| Claude | 專案根目錄的 `CLAUDE.md` |
| Codex | 專案根目錄的 `AGENTS.md` |

為什麼需要常駐指令檔？SKILL 是「按需觸發」的——Claude Code / Codex 平常只載入 SKILL 的名稱與說明，模型要自己決定去叫它才會執行內文。像「動檔前一定要先開對話紀錄」這種每次都要做的規則，光靠 SKILL 不夠可靠，AI 常常直接改檔、沒開對話紀錄，改動就被當成人工改動、只出現在「現在的改動」。`CLAUDE.md`（Claude）與 `AGENTS.md`（Codex）這兩個檔案每次開始對話都一定會被載入，把規則常駐進去，AI 才會穩定地自動記錄。（Cursor 會把 SKILL 較積極地帶進每一輪，所以通常不需要這一步。）

這兩個檔案是**自動維護**的：

- 只會更新 `<!-- avc-shiguangben:begin ... end -->` 標記之間那一段，**不會蓋掉你自己在 `CLAUDE.md` / `AGENTS.md` 寫的其他內容**。
- 切換 Agent 時，會自動清掉另一個 Agent 的舊區塊，避免兩份規則互相衝突。
- 已經在記錄的舊專案，只要**再開一次時光本網頁**（或在網頁重新選一次 Agent），就會自動補上。

**3. 自動記錄 hook（只有選 Claude 時，寫進 `.claude/settings.json`）**

這是最保險的一層，**完全不靠模型記得**。選 Claude 後會在 `.claude/settings.json` 加入 Claude Code 的 hook：對話開始自動開一個對話紀錄、每輪結束若有改動就自動記住、對話結束收尾。所以只要是用 **Claude Code（終端機／IDE 版）** 改檔，改完就一定會被記錄，不會掉進「未記住」。

- 只會加／換掉我們自己的項目（指令含 `_autohook`），**不會動到你原本的 hooks 或 permissions**；`settings.json` 若無法解析就完全不碰。
- 切換到別的 Agent 會自動移除這些 hook。
- ⚠️ 這些 hook 只對 **Claude Code** 有效。**Claude 桌面版 App（Cowork）不會讀資料夾裡的 `.claude/` 設定**，用桌面版 App 改檔要另外靠一個 Cowork 技能來自動記錄。

> 用哪種工具會自動記錄？Cursor ✅、Claude Code ✅、Codex ✅（讀 `AGENTS.md`）；Claude 桌面版 App 需另裝 Cowork 技能。

Agent 請在該資料夾執行對應的啟動檔。

```text
# Mac / Linux
python3 .avc/avc.py status

# Windows（自動使用打包好的 avc.exe，找不到才退回 python，不需要 py）
.avc\avc.cmd status
```

> **路徑會自動偵測**：`.avc/avc.py` 會依序嘗試「已安裝 → 環境變數 `AVC_HOME` → 安裝當下記錄的路徑 → 家目錄／桌面等常見位置 → 連線掛載點 `~/mnt/`」來找到時光本主程式，正常情況免設定。若你把時光本資料夾搬家後跑不動，設一個環境變數 `AVC_HOME` 指到時光本資料夾即可，**不必重新 init**。

每個被記錄的資料夾有 `.avc/avc.sqlite`。專案列表在使用者目錄下的 `.avc/registry.sqlite`。
