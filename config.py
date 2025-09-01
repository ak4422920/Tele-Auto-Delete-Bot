import os

API_ID = os.environ.get("API_ID","")
API_HASH = os.environ.get("API_HASH","")
BOT_TOKEN = os.environ.get("BOT_TOKEN","")
DATABASE_URL = os.environ.get("DATABASE_URL","")
BOT_USERNAME = os.environ.get("BOT_USERNAME","Testkliyebot") # Without @
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "AkMoviesHubBackup")  # without @
PORT = int(os.environ.get("PORT", 8080))  # for Flask binding (Koyeb)
OWNER_ID = int(os.environ.get("OWNER_ID", "8371607189"))  # your Telegram user ID
