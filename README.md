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

選好 Agent 後，會在資料夾寫入：

| Agent | SKILL 位置 |
| --- | --- |
| Cursor | `.cursor/skills/avc-shiguangben/` |
| Claude | `.claude/skills/avc-shiguangben/` |
| Codex | `.agents/skills/avc-shiguangben/` |

Agent 請在該資料夾執行對應的啟動檔。

```text
# Mac / Linux
python3 .avc/avc.py status

# Windows（自動使用打包好的 avc.exe，找不到才退回 python，不需要 py）
.avc\avc.cmd status
```

每個被記錄的資料夾有 `.avc/avc.sqlite`。專案列表在使用者目錄下的 `.avc/registry.sqlite`。
