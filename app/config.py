import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOSS_ID = int(os.getenv("BOSS_ID")) if os.getenv("BOSS_ID") else None
ALERT_GROUP_ID = int(os.getenv("GROUP_ID")) if os.getenv("GROUP_ID") else None
THREAD_TEST = int(os.getenv("THREAD_TEST")) if os.getenv("THREAD_TEST") else None

TRIGGERS_TO_BOSS = ["@longdy_seng", "plan", "operation", "production","apple","kiss","you","longdy_seng","longdy"]
TRIGGERS_TO_GROUP = ["yang",]


# Map trigger words to boss groups (and optional topic/thread id)
ROUTES = {
    "kiss": {
        "boss_chat": BOSS_ID,  # TODO: replace with real boss group chat_id
        "thread_id": None,           # or an integer thread/topic id if you use topics
    },
    "option": {
        "boss_chat": ALERT_GROUP_ID, # another boss group
        "thread_id": THREAD_TEST,
    },
    # add more triggers as needed
}
