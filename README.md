```markdown
# Telegram Alert Bot

Small Telegram bot that watches groups for trigger words and sends alerts to either a **personal chat** or a **team alert group**. Replies to alerts are forwarded back to the original group message.

---

## Config files

### `app/config.py`

Main place to configure behavior:

```
# app/config.py

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Personal chat where boss receives some alerts
BOSS_ID = 123456789

# Group where team-level alerts are posted
ALERT_GROUP_ID = -1001234567890

# Trigger words that send alerts to the boss
TRIGGERS_TO_BOSS = [
    "kien",
    "boss",
    "@kiengyang",
]

# Trigger words that send alerts to the alert group
TRIGGERS_TO_GROUP = [
    "support",
    "help team",
    "urgent group",
]
```

Change these values to match your setup (token + IDs + trigger keywords).

### Environment variables (optional)

If you prefer, you can store secrets in environment variables and read them inside `config.py`, for example:

```
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOSS_ID = int(os.getenv("BOSS_ID", "0"))
ALERT_GROUP_ID = int(os.getenv("ALERT_GROUP_ID", "0"))

TRIGGERS_TO_BOSS = os.getenv("TRIGGERS_TO_BOSS", "kien,boss,@kiengyang").split(",")
TRIGGERS_TO_GROUP = os.getenv("TRIGGERS_TO_GROUP", "support,help team,urgent group").split(",")
```

Then set these in `docker-compose.yml` or a `.env` file.

---

## Main bot file

- **`app/bot.py`** is the main entrypoint.
- It:
  - Starts the Telegram client
  - Watches groups for triggers
  - Sends alerts with inline buttons (**Reply / Ignore**)
  - Forwards replies back to the original group
  - Implements `/start`, `/summary`, `/clear_today`
  - Uses `app/db.json` as a simple JSON database

You normally do not need to change `bot.py` unless you want to change logic.

---

## Docker deployment

### 1. `requirements.txt`

Example:

```
python-telegram-bot~=21.0
httpx
```

### 2. `Dockerfile`

```
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["python", "-u", "app/bot.py"]
```

### 3. `docker-compose.yml`

```
version: "3.9"

services:
  telegram-bot:
    build: .
    container_name: telegram-alert-bot
    restart: unless-stopped
    volumes:
      # Persist the JSON DB on the host
      - ./app/db.json:/app/app/db.json

    # If using a .env file or env vars with config.py:
    # env_file:
    #   - .env
    # or:
    # environment:
    #   BOT_TOKEN: "123456789:AA..."
    #   BOSS_ID: "123456789"
    #   ALERT_GROUP_ID: "-1001234567890"
```

### 4. Optional `.env` file

If you use environment variables for secrets:

```
BOT_TOKEN=123456789:AA...
BOSS_ID=123456789
ALERT_GROUP_ID=-1001234567890

TRIGGERS_TO_BOSS=kien,boss,@kiengyang
TRIGGERS_TO_GROUP=support,help team,urgent group
```

Make sure `docker-compose.yml` includes:

```
env_file:
  - .env
```

---

## How to deploy

From the project root (where `docker-compose.yml` is):

```
# Build the image
docker compose build

# Start the bot in the background
docker compose up -d

# See logs
docker compose logs -f
```

To stop:

```
docker compose down
```

After changing `config.py`, `.env`, or dependencies:

```
docker compose down
docker compose build
docker compose up -d
```

This is all your boss needs:  
- Edit `app/config.py` (or `.env`) to set token, IDs, and triggers.  
- Use `docker compose build` and `docker compose up -d` to run the bot.
