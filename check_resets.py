import os
import sys
import time
import argparse
import logging
from datetime import datetime, timezone, timedelta
import requests

# 確保在 Windows 終端機正常輸出繁體中文字元
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 建立日誌格式
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("codex-notifier")

# 簡易讀取 .env 檔案（無須額外安裝 python-dotenv 也能運作）
def load_env(env_path=".env"):
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val

load_env()

# 設定參數
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
API_URL = os.environ.get("CODEX_API_URL", "https://codex-resets.com/api/v1/resets").strip()
STATE_FILE = os.environ.get("STATE_FILE", "last_reset_id.txt").strip()
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "120"))
MENTION = os.environ.get("DISCORD_MENTION", "").strip()  # 例如 @everyone 或 <@&身分組ID>

# 時區設定（預設台灣時間 UTC+8）
TZ_UTC8 = timezone(timedelta(hours=8))


def format_iso_time(iso_str: str) -> tuple[str, str]:
    """將 ISO 8601 時間轉換為台灣時間 (UTC+8) 與 UTC 時間字串"""
    if not iso_str:
        return "未知", "未知"
    try:
        # 兼容結尾的 Z
        clean_iso = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        dt_utc8 = dt.astimezone(TZ_UTC8)
        dt_utc = dt.astimezone(timezone.utc)
        return (
            dt_utc8.strftime("%Y-%m-%d %H:%M:%S (UTC+8)"),
            dt_utc.strftime("%Y-%m-%d %H:%M:%S (UTC)"),
        )
    except Exception:
        return iso_str, iso_str


def get_latest_reset() -> dict | None:
    """呼叫 codex-resets.com API 取得最新一筆重置紀錄"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CodexResetNotifier/1.0"
    }
    try:
        resp = requests.get(API_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return data[0]
        logger.warning("API 回傳成功，但沒有任何資料。")
        return None
    except requests.RequestException as e:
        logger.error(f"連線至 API 失敗: {e}")
        return None


def read_last_id() -> str:
    """讀取上次已記錄的 reset ID"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"讀取狀態檔 {STATE_FILE} 失敗: {e}")
    return ""


def save_last_id(reset_id: str) -> None:
    """儲存最新的 reset ID"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(reset_id)
        logger.info(f"已更新記錄 ID: {reset_id}")
    except Exception as e:
        logger.error(f"寫入狀態檔 {STATE_FILE} 失敗: {e}")


def build_discord_payload(reset_item: dict, is_test: bool = False) -> dict:
    """建立發送到 Discord Webhook 的 Embed 內容"""
    reset_type = reset_item.get("reset_type", "regular").lower()
    text = reset_item.get("text", "（無詳細說明）")
    source_url = reset_item.get("source", {}).get("url", "https://codex-resets.com")
    announced_at = reset_item.get("announced_at", "")

    time_tw, time_utc = format_iso_time(announced_at)

    # 根據重置類型決定顏色與標籤
    # regular: 綠色 (0x2ecc71), banked: 金橙色 (0xf39c12), test: 藍色 (0x3498db)
    if is_test:
        color = 0x3498DB
        title = "🧪 [測試通知] Codex 重置監控機器人測試中"
    elif reset_type == "banked":
        color = 0xF39C12
        title = "🎁 Codex 額度已重置 (Banked 額外重置)！"
    else:
        color = 0x2ECC71
        title = "🚨 Codex 額度已重置 (Regular 常規重置)！"

    fields = [
        {"name": "⏰ 台灣時間", "value": f"`{time_tw}`", "inline": True},
        {"name": "🌐 UTC 時間", "value": f"`{time_utc}`", "inline": True},
        {"name": "🏷️ 類型", "value": f"`{reset_type.upper()}`", "inline": True},
    ]

    if source_url:
        fields.append({
            "name": "🔗 消息來源",
            "value": f"[點擊查看原始貼文]({source_url})",
            "inline": False,
        })

    payload = {
        "embeds": [
            {
                "title": title,
                "description": f"**發布內容：**\n{text}",
                "url": source_url or "https://codex-resets.com",
                "color": color,
                "fields": fields,
                "footer": {
                    "text": "資料來源: codex-resets.com • Codex Reset Notifier",
                    "icon_url": "https://codex-resets.com/favicon.ico",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }

    if MENTION and not is_test:
        payload["content"] = MENTION

    return payload


def send_discord_webhook(payload: dict) -> bool:
    """發送訊息至 Discord Webhook"""
    if not DISCORD_WEBHOOK_URL:
        logger.error("錯誤: 尚未設定 DISCORD_WEBHOOK_URL！請在 .env 檔案中填入 Webhook 網址。")
        return False

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            logger.info("✅ 成功發送 Discord Webhook 通知！")
            return True
        elif resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            logger.warning(f"Discord 觸發頻率限制 (Rate Limit)，需等待 {retry_after} 秒")
            return False
        else:
            logger.error(f"發送 Discord 失敗，狀態碼: {resp.status_code}, 內容: {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"發送 Discord Webhook 連線失敗: {e}")
        return False


def check_and_notify(force_test: bool = False) -> bool:
    """執行檢查邏輯"""
    logger.info("正在檢查 codex-resets.com 最新動態...")
    latest = get_latest_reset()
    if not latest:
        return False

    latest_id = str(latest.get("id", ""))
    last_id = read_last_id()

    logger.info(f"API 最新 ID: {latest_id} | 本地記錄 ID: {last_id or '(尚未記錄)'}")

    # 測試模式：直接發送最新這筆作為測試通知
    if force_test:
        logger.info("觸發測試發送模式...")
        payload = build_discord_payload(latest, is_test=True)
        return send_discord_webhook(payload)

    # 首次執行（若尚未有記錄檔）
    if not last_id:
        logger.info(f"第一次啟動，記錄目前最新重置 ID ({latest_id})，不發送歷史通知。")
        save_last_id(latest_id)
        return True

    # 發現新的重置通知
    if latest_id != last_id:
        logger.info(f"🎉 發現新重置！ID: {latest_id}")
        payload = build_discord_payload(latest, is_test=False)
        success = send_discord_webhook(payload)
        if success:
            save_last_id(latest_id)
            return True
        else:
            logger.warning("Discord 發送未成功，暫不更新狀態檔，下次輪詢重試。")
            return False
    else:
        logger.info("目前無新重置紀錄。")
        return True


def run_loop(interval: int):
    """循環輪詢模式"""
    logger.info(f"🚀 啟動輪詢守護模式，每 {interval} 秒檢查一次...")
    logger.info("按下 Ctrl + C 可隨時停止程式。")
    try:
        while True:
            check_and_notify()
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("使用者中斷，停止輪詢。")


def main():
    parser = argparse.ArgumentParser(description="Codex 額度重置監控機器人")
    parser.add_argument("--test", action="store_true", help="立即向 Discord 發送一則測試通知")
    parser.add_argument("--loop", type=int, nargs="?", const=CHECK_INTERVAL_SECONDS, default=None,
                        help=f"循環輪詢模式（可指定間隔秒數，預設 {CHECK_INTERVAL_SECONDS} 秒）")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL_SECONDS,
                        help=f"輪詢檢查間隔秒數（預設 {CHECK_INTERVAL_SECONDS} 秒）")
    args = parser.parse_args()

    if args.test:
        success = check_and_notify(force_test=True)
        sys.exit(0 if success else 1)
    elif args.loop is not None:
        interval = args.loop if args.loop > 0 else args.interval
        run_loop(interval)
    else:
        # 單次執行（適用於 GitHub Actions 或 Windows 排程作業）
        check_and_notify()


if __name__ == "__main__":
    main()
