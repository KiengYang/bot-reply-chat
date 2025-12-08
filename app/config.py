import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOSS_ID = int(os.getenv("BOSS_ID")) if os.getenv("BOSS_ID") else None

TRIGGER_WORDS = ["longdy", "plan", "operation", "longdy_seng", "production",]
