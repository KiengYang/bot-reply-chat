import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOSS_ID = int(os.getenv("BOSS_ID")) if os.getenv("BOSS_ID") else None
ALERT_GROUP_ID = int(os.getenv("GROUP_ID")) if os.getenv("GROUP_ID") else None
THREAD_TEST = int(os.getenv("THREAD_TEST")) if os.getenv("THREAD_TEST") else None

TRIGGERS_TO_BOSS = ["longdy" "longdy_seng","@longdy_seng"]
TRIGGERS_TO_GROUP = []


# Map trigger words to boss groups (and optional topic/thread id)
ROUTES = {
    # Production topic
    "production": {
        "boss_chat": -1003373605091,   # Operation Support Site
        "thread_id": 166,              # Production topic
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "operation": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "plan": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "planing": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "schudule": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "measphirom": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "phirom": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },
    "kimyonje": {
        "boss_chat": -1003373605091,
        "thread_id": 166,
        "mentions": ["@Measphirom", "@kimyonje"],
    },

    # QC topic
    "qc": {
        "boss_chat": -1003373605091,
        "thread_id": 168,
        "mentions": ["@sovann_raksmey"],
    },
    "qc team": {
        "boss_chat": -1003373605091,
        "thread_id": 168,
        "mentions": ["@sovann_raksmey"],
    },
    "quality": {
        "boss_chat": -1003373605091,
        "thread_id": 168,
        "mentions": ["@sovann_raksmey"],
    },
    "inspection": {
        "boss_chat": -1003373605091,
        "thread_id": 168,
        "mentions": ["@sovann_raksmey"],
    },
    "sovann_raksmey": {
        "boss_chat": -1003373605091,
        "thread_id": 168,
        "mentions": ["@sovann_raksmey"],
    },
    "raksmey": {
        "boss_chat": -1003373605091,
        "thread_id": 168,
        "mentions": ["@sovann_raksmey"],
    },

    # Warehouse topic
    "warehouse": {
        "boss_chat": -1003373605091,
        "thread_id": 161,
        "mentions": ["@Nao_sophorn"],
    },
    "stock": {
        "boss_chat": -1003373605091,
        "thread_id": 161,
        "mentions": ["@Nao_sophorn"],
    },
    "inventory": {
        "boss_chat": -1003373605091,
        "thread_id": 161,
        "mentions": ["@Nao_sophorn"],
    },
    "nao_sophorn": {
        "boss_chat": -1003373605091,
        "thread_id": 161,
        "mentions": ["@Nao_sophorn"],
    },
    "sophorn": {
        "boss_chat": -1003373605091,
        "thread_id": 161,
        "mentions": ["@Nao_sophorn"],
    },

    # E&E topic
    "siphan_tnp": {
        "boss_chat": -1003373605091,
        "thread_id": 164,
        "mentions": ["@SIPHAN_TNP"],
    },
    "machine": {
        "boss_chat": -1003373605091,
        "thread_id": 164,
        "mentions": ["@SIPHAN_TNP"],
    },
    "repair": {
        "boss_chat": -1003373605091,
        "thread_id": 164,
        "mentions": ["@SIPHAN_TNP"],
    },
    "maintenance": {
        "boss_chat": -1003373605091,
        "thread_id": 164,
        "mentions": ["@SIPHAN_TNP"],
    },

    # Logistic topic
    "tola": {
        "boss_chat": -1003373605091,
        "thread_id": 158,
        "mentions": ["@HTL_Tola"],
    },
    "delivery": {
        "boss_chat": -1003373605091,
        "thread_id": 158,
        "mentions": ["@HTL_Tola"],
    },
    "logistic": {
        "boss_chat": -1003373605091,
        "thread_id": 158,
        "mentions": ["@HTL_Tola"],
    },
}
