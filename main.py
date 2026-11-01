import sys
import threading

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn
import config
import database
from server import app
from bot import run_bot_polling

def start_bot_thread():
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    return bot_thread

if __name__ == "__main__":
    database.init_db()
    
    # Start Telegram bot in background
    if config.BOT_TOKEN:
        start_bot_thread()
    else:
        print("⚠️ BOT_TOKEN is not set in .env! Telegram bot polling will not run.")

    print("\n" + "=" * 60)
    print("  🚀 Додаток для обліку піддонів успішно запущено!")
    print(f"  🌐 Локальний веб-інтерфейс: http://localhost:{config.PORT}")
    print("  🤖 Telegram-бот слухає команди: @pallet_stock_tracker_bot")
    print("=" * 60 + "\n")

    try:
        uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")
    except (KeyboardInterrupt, SystemExit):
        print("\nСервер зупинено.")
        sys.exit(0)
