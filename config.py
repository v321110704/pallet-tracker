import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_webapp_url() -> str:
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
    return os.getenv("WEBAPP_URL", "").strip()

load_dotenv(os.path.join(BASE_DIR, ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
WEBAPP_URL = get_webapp_url()
