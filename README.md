# Codex 額度重置監控機器人 (Discord Webhook Notifier)

此專案透過監控 [codex-resets.com](https://codex-resets.com/) 的公開 API，當偵測到 OpenAI Codex / ChatGPT Work 額度重置時，即時發送美觀的 Embed 訊息至你的 Discord 頻道！

---

## 🌟 功能特色

- **免 API 金鑰**：使用官方公開重置端點，完全免費。
- **美觀 Discord Embed**：包含重置類型標籤（Regular 常規 / Banked 額外累積）、原文內容、消息來源連結，並自動轉換為 **台灣時間 (UTC+8)** 與 **UTC 時間**。
- **防重複發送**：自動維護 `last_reset_id.txt`，重置公告只會發送一次。
- **支援兩種運行方式**：
  1. **本機 / NAS / VPS**：雙擊 `start_bot.bat` 或設定常駐輪詢，每 1~2 分鐘即時監控。
  2. **GitHub Actions 雲端自動化**：完全免費，不用開電腦、不用租伺服器，每 5 分鐘自動排程。
- **一鍵測試指令**：支援 `--test` 參數，立即發送測試訊息確認 Webhook 是否正常。

---

## 🚀 快速上手教學

### 步驟 1：取得 Discord Webhook 網址

1. 開啟 Discord，進入你想接收通知的頻道。
2. 點擊頻道名稱旁的 **⚙️「編輯頻道」**。
3. 點選左側選單的 **「整合 (Integrations)」** -> **「Webhook」**。
4. 點擊 **「建立 Webhook」**（可自訂名稱為「Codex 重置提醒」與大頭貼）。
5. 點擊 **「複製 Webhook 網址」**。

---

### 步驟 2：設定 `.env` 檔案

在專案目錄下開啟 `.env` 檔案，填入剛才複製的 Webhook 網址：

```ini
# 請在此貼上你的 Discord Webhook 網址
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/abcdefg...

# 檢查間隔（秒），預設 120 秒（2 分鐘）
CHECK_INTERVAL_SECONDS=120

# 選擇性：是否 Tag 所有人（例如 @everyone）或留空
DISCORD_MENTION=
```

---

### 步驟 3：測試發送

在專案目錄下開啟終端機，執行以下指令驗證 Webhook 是否正常：

```bash
python check_resets.py --test
```

若設定無誤，你的 Discord 頻道將會立刻收到一則「🧪 [測試通知]」的 Embed 訊息！

---

## ⚙️ 運行方式

### 方式 A：本機 / Windows 雙擊運行（最簡單、最即時）

直接雙擊專案目錄下的 **`start_bot.bat`** 即可啟動輪詢！
預設每 2 分鐘檢查一次 API，若發現最新重置動態將自動推送到 Discord。

若在終端機中運行：
```bash
# 預設持續輪詢（每 120 秒）
python check_resets.py --loop

# 自訂輪詢秒數（例如每 60 秒）
python check_resets.py --loop 60

# 單次執行（適用於 Windows 工作排程器）
python check_resets.py
```

---

### 方式 B：GitHub Actions 雲端自動化（全免費、免開電腦）

如果你不想一直開著電腦，可以直接將這個專案推送到 GitHub 私人或公開 Repository：

1. **上傳專案至 GitHub**：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <你的 GitHub 倉庫網址>
   git push -u origin main
   ```
2. **設定 GitHub Secrets**：
   - 進入你的 GitHub Repo -> **Settings** -> **Secrets and variables** -> **Actions**。
   - 點擊 **New repository secret**：
     - Name: `DISCORD_WEBHOOK_URL`
     - Value: `你的 Discord Webhook 網址`
   - （可選）如果需要 @everyone，可新增 `DISCORD_MENTION`。
3. **完成！**
   - 專案已內建 `.github/workflows/check_resets.yml`，GitHub Actions 會每 5 分鐘自動執行一次，並在發現新重置時更新 `last_reset_id.txt` 自動推送到 Discord。

---

## 📁 檔案結構說明

```text
tibo通知機器人/
├── check_resets.py                  # 核心監控與推送腳本
├── start_bot.bat                    # Windows 一鍵啟動腳本
├── .env                             # 設定檔（Webhook 網址與頻率）
├── .env.example                     # 設定範本檔
├── requirements.txt                 # Python 依賴庫 (requests)
├── .gitignore                       # 忽略機密與快取檔案
├── README.md                        # 本說明文件
└── .github/
    └── workflows/
        └── check_resets.yml         # GitHub Actions 免費定時執行排程
```
