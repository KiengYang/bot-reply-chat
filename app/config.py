import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOSS_ID = int(os.getenv("BOSS_ID")) if os.getenv("BOSS_ID") else None
ALERT_GROUP_ID = int(os.getenv("GROUP_ID")) if os.getenv("GROUP_ID") else None

TRIGGERS_TO_BOSS = ["longdy", "plan", "operation", "longdy_seng", "production",]
TRIGGERS_TO_GROUP = ["yang",]

