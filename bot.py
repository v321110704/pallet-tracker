import time
import logging
import requests
from typing import Optional

import config
import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PalletBot")

API_BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"

def set_bot_menu_button(webapp_url: str, chat_id: Optional[int] = None):
    if not webapp_url:
        return
    try:
        url = f"{API_BASE}/setChatMenuButton"
        payload = {
            "menu_button": {
                "type": "web_app",
                "text": "📦 Облік піддонів",
                "web_app": {"url": webapp_url}
            }
        }
        if chat_id:
            payload["chat_id"] = chat_id
        res = requests.post(url, json=payload, timeout=10)
        logger.info(f"Set menu button response (chat_id={chat_id}): {res.json()}")
    except Exception as e:
        logger.error(f"Error setting menu button: {e}")

def set_bot_commands():
    try:
        url = f"{API_BASE}/setMyCommands"
        commands = [
            {"command": "start", "description": "Головне меню та запуск додатку"},
            {"command": "report", "description": "Отримати поточний звіт про остаток"},
            {"command": "stock", "description": "Швидкий залишок на складі"}
        ]
        requests.post(url, json={"commands": commands}, timeout=10)
    except Exception as e:
        logger.error(f"Error setting commands: {e}")

def send_message(chat_id: int, text: str, reply_markup: Optional[dict] = None):
    try:
        url = f"{API_BASE}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        res = requests.post(url, json=payload, timeout=10)
        logger.info(f"Send message to {chat_id}: status={res.status_code}")
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")

def handle_update(update: dict):
    # Message update
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()
        user_name = msg.get("from", {}).get("first_name", "Користувач")
        
        if not chat_id:
            return

        webapp_url = config.get_webapp_url()

        if text.startswith("/start"):
            logger.info(f"User {user_name} ({chat_id}) triggered /start. WebApp URL: '{webapp_url}'")
            
            # Update menu button specifically for this user
            if webapp_url:
                set_bot_menu_button(webapp_url, chat_id=chat_id)

            welcome_text = (
                f"👋 <b>Вітаю, {user_name}!</b>\n\n"
                f"Це офіційний додаток для <b>обліку малих піддонів</b> на складі.\n\n"
                f"📌 <b>Можливості:</b>\n"
                f"• Внесення набитих піддонів (Любота В. та Галкін В.)\n"
                f"• Розрахунок залишку на складі в реальному часі\n"
                f"• Фіксація та історія відвантажень\n"
                f"• Автоматичний підрахунок за 15 робочих днів\n"
                f"• Формування щоденного звіту для керівництва"
            )
            
            inline_keyboard = []
            if webapp_url:
                inline_keyboard.append([
                    {"text": "📱 Відкрити облік піддонів", "web_app": {"url": webapp_url}}
                ])
            else:
                welcome_text += "\n\n💡 <i>(Запустіть Cloudflare Tunnel для активації кнопки Mini App)</i>"

            inline_keyboard.append([
                {"text": "📊 Отримати звіт у чат", "callback_data": "get_report"}
            ])

            reply_markup = {"inline_keyboard": inline_keyboard}
            send_message(chat_id, welcome_text, reply_markup=reply_markup)

        elif text in ["/report", "/stock", "Звіт", "Остаток"]:
            report_text = database.generate_report_text()
            send_message(chat_id, f"<pre>{report_text}</pre>")
            
    # Callback query update
    elif "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb.get("id")
        data = cb.get("data")
        msg = cb.get("message", {})
        chat_id = msg.get("chat", {}).get("id")

        try:
            requests.post(f"{API_BASE}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
        except Exception:
            pass

        if data == "get_report" and chat_id:
            report_text = database.generate_report_text()
            send_message(chat_id, f"<pre>{report_text}</pre>")

def run_bot_polling():
    if not config.BOT_TOKEN:
        logger.warning("BOT_TOKEN is not configured! Telegram bot polling skipped.")
        return

    logger.info("Initializing Telegram bot...")
    set_bot_commands()
    
    current_url = config.get_webapp_url()
    if current_url:
        set_bot_menu_button(current_url)

    offset = 0
    logger.info("Telegram Bot polling started successfully!")

    while True:
        try:
            url = f"{API_BASE}/getUpdates?offset={offset}&timeout=20"
            res = requests.get(url, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        try:
                            handle_update(update)
                        except Exception as e:
                            logger.error(f"Error handling update: {e}")
            elif res.status_code == 409:
                logger.warning("Conflict: Another bot instance is polling. Waiting 5s...")
                time.sleep(5)
            else:
                time.sleep(2)
        except Exception as e:
            logger.error(f"Polling connection error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    database.init_db()
    run_bot_polling()
