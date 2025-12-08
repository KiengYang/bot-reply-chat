import json
import os
from datetime import datetime, time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.request import HTTPXRequest

# ------------------- CONFIG -------------------
from app.config import BOT_TOKEN, BOSS_ID, TRIGGER_WORDS

DB_FILE = "app/db.json"

# key = BOSS_ID, value = message key in DB
reply_map = {}


# ------------------- DATABASE HELPERS -------------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)


# ------------------- COMMANDS -------------------
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is running successfully.")


async def manual_summary(update, context: ContextTypes.DEFAULT_TYPE):
    """Boss can type /summary to see pending & ignored messages"""
    db = load_db()
    items = [
        entry
        for entry in db.values()
        if entry.get("status") in ("pending", "ignored")
    ]

    if not items:
        await update.message.reply_text("📊 No pending or ignored messages today.")
        return

    # Sort by time (oldest first)
    try:
        items.sort(key=lambda e: datetime.fromisoformat(e["time"]))
    except Exception:
        pass

    msg = "📊 **Summary — Pending & Ignored Messages**\n\n"
    for e in items:
        status = e.get("status", "unknown").capitalize()
        try:
            dt = datetime.fromisoformat(e["time"])
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = e.get("time", "Unknown time")

        msg += (
            f"- [{status}] From *{e['sender']}* in *{e.get('group_title', 'group')}* "
            f"at `{time_str}`:\n"
        )
        msg += f"  {e['text'][:100]}...\n"

        group_username = e.get("group_username")
        group_id = e.get("group_id")
        message_id = e.get("message_id")

        if group_username:
            msg += (
                f"  Open: tg://resolve?domain={group_username}"
                f"&post={message_id}\n\n"
            )
        elif str(group_id).startswith("-100"):
            chat_id_for_link = str(group_id)[4:]
            msg += (
                f"  Open: https://t.me/c/{chat_id_for_link}/{message_id}\n\n"
            )
        else:
            msg += f"  Message ID: {message_id}\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def clear_today(update, context: ContextTypes.DEFAULT_TYPE):
    """Clear today's pending & ignored messages from the database."""
    # Only boss can clear
    if update.effective_user.id != BOSS_ID:
        return

    db = load_db()
    if not db:
        await update.message.reply_text("🧹 Nothing to clear.")
        return

    today = datetime.now().date()
    new_db = {}
    removed = 0

    for key, entry in db.items():
        status = entry.get("status")
        t_str = entry.get("time")

        # If time is missing or invalid, keep the entry
        try:
            dt = datetime.fromisoformat(t_str) if t_str else None
        except Exception:
            dt = None

        is_today = dt is not None and dt.date() == today
        is_target_status = status in ("pending", "ignored")

        # Remove only today's pending/ignored; keep everything else
        if is_today and is_target_status:
            removed += 1
            continue

        new_db[key] = entry

    save_db(new_db)

    if removed == 0:
        await update.message.reply_text("🧹 No pending or ignored messages for today to clear.")
    else:
        await update.message.reply_text(f"🧹 Cleared {removed} pending/ignored messages for today.")


# ------------------- MESSAGE WATCHER (GROUPS) -------------------
async def watch_messages(update, context: ContextTypes.DEFAULT_TYPE):
    """Detect trigger words or boss mentions in groups"""
    if not update.message or not update.message.text:
        return

    # Only care about group chats here
    if update.message.chat.type not in ("group", "supergroup"):
        return

    text = update.message.text.lower()
    triggered = False
    print("New message:", text)
    print("Chat info:", update.message.chat)

    # Check trigger words
    for word in TRIGGER_WORDS:
        if word.lower() in text:
            triggered = True
            break

    # Check if boss is mentioned (@kiengyang)
    if update.message.entities:
        for entity in update.message.entities:
            if (
                entity.type == "mention"
                and "@kiengyang" in update.message.text.lower()
            ):
                triggered = True

    if not triggered:
        return

    # Save message info
    db = load_db()
    key = f"{update.message.chat.id}_{update.message.message_id}"

    db[key] = {
        "group_id": update.message.chat.id,
        "group_title": update.message.chat.title or "group",
        "group_username": update.message.chat.username or "",
        "message_id": update.message.message_id,
        "text": update.message.text,
        "sender": update.message.from_user.full_name,
        "time": datetime.now().isoformat(),
        "status": "pending",
    }
    save_db(db)

    # ------------------- BUILD BUTTONS -------------------
    open_url = None
    chat_id_str = str(update.message.chat.id)

    if update.message.chat.username:
        # public group/channel with username
        open_url = (
            f"tg://resolve?domain={update.message.chat.username}"
            f"&post={update.message.message_id}"
        )
    elif chat_id_str.startswith("-100"):
        # private supergroup/channel
        chat_id_for_link = chat_id_str[4:]
        open_url = f"https://t.me/c/{chat_id_for_link}/{update.message.message_id}"
    else:
        # normal private group: no message link in Telegram API
        print("No open_url for this chat (ChatType.GROUP).")

    buttons = [[InlineKeyboardButton("Reply", callback_data=f"reply|{key}")]]
    if open_url:
        buttons[0].append(
            InlineKeyboardButton("Open in group", url=open_url)
        )
    buttons.append(
        [InlineKeyboardButton("Ignore", callback_data=f"ignore|{key}")]
    )
    kb = InlineKeyboardMarkup(buttons)

    # Forward alert to boss
    await context.bot.send_message(
        chat_id=BOSS_ID,
        text=(
            f"⚠ **Mention Alert**\n"
            f"From: {update.message.from_user.full_name}\n"
            f"Group: {update.message.chat.title}\n\n"
            f"{update.message.text}"
        ),
        reply_markup=kb,
        parse_mode="Markdown",
    )

    print(f"Forwarded message {key} to boss with buttons.")


# ------------------- INLINE BUTTON HANDLER -------------------
async def button_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")
    action = data[0]
    key = data[1]

    print("Button clicked:", data)
    db = load_db()

    if key not in db:
        await query.edit_message_text("❌ Message expired or not found.")
        return

    if action == "ignore":
        db[key]["status"] = "ignored"
        save_db(db)
        await query.edit_message_text("Ignored.")
        return

    if action == "reply":
        reply_map[BOSS_ID] = key
        print(f"Reply mode ON for boss, key={key}")
        await query.edit_message_text(
            "✏️ Reply mode activated. Send your reply below in this private chat and it will be forwarded to the group automatically."
        )


# ------------------- BOSS REPLY HANDLER -------------------
async def reply_to_group(update, context: ContextTypes.DEFAULT_TYPE):
    """Forward boss reply to the original group (private or public)"""
    if not update.message:
        return

    # Only messages from boss are interesting here
    if update.effective_user.id != BOSS_ID:
        return

    print("Boss sent:", update.message)
    print("Boss chat info:", update.message.chat)

    if BOSS_ID not in reply_map:
        print("Boss message but reply_map is empty -> ignore.")
        return

    key = reply_map[BOSS_ID]
    db = load_db()

    if key not in db:
        await update.message.reply_text("❌ Original message expired.")
        del reply_map[BOSS_ID]
        return

    entry = db[key]
    print("reply_to_group triggered")
    print("Forwarding boss reply message")
    print("Target chat_id:", entry["group_id"], "message_id:", entry["message_id"])

    # Forward the boss's message (text, voice, photo, etc.)
    await update.message.forward(chat_id=entry["group_id"])

    db[key]["status"] = "replied"
    save_db(db)

    await update.message.reply_text("✅ Your reply has been forwarded.")
    del reply_map[BOSS_ID]
    print("Reply mode OFF for boss")


# ------------------- DAILY SUMMARY -------------------
async def daily_summary(job):
    """Send daily summary of pending and ignored messages, with timestamps."""
    db = load_db()

    items = [
        entry
        for entry in db.values()
        if entry.get("status") in ("pending", "ignored")
    ]

    if not items:
        await job.bot.send_message(BOSS_ID, "📊 No pending or ignored messages today.")
        return

    # Sort by time (oldest first)
    try:
        items.sort(key=lambda e: datetime.fromisoformat(e["time"]))
    except Exception:
        pass

    msg = "📊 **Daily Summary — Pending & Ignored Messages**\n\n"
    for e in items:
        status = e.get("status", "unknown").capitalize()
        try:
            dt = datetime.fromisoformat(e["time"])
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = e.get("time", "Unknown time")

        msg += (
            f"- [{status}] From *{e['sender']}* in *{e.get('group_title', 'group')}* "
            f"at `{time_str}`:\n"
        )
        msg += f"  {e['text'][:100]}...\n"

        group_username = e.get("group_username")
        group_id = e.get("group_id")
        message_id = e.get("message_id")

        if group_username:
            msg += (
                f"  Open: tg://resolve?domain={group_username}"
                f"&post={message_id}\n\n"
            )
        elif str(group_id).startswith("-100"):
            chat_id_for_link = str(group_id)[4:]
            msg += (
                f"  Open: https://t.me/c/{chat_id_for_link}/{message_id}\n\n"
            )
        else:
            msg += f"  Message ID: {message_id}\n\n"

    await job.bot.send_message(BOSS_ID, msg, parse_mode="Markdown")


# ------------------- MAIN -------------------
def main():
    request = HTTPXRequest(
        connect_timeout=20.0,
        read_timeout=20.0,
        write_timeout=20.0,
        pool_timeout=5.0,
    )

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", manual_summary))
    app.add_handler(CommandHandler("clear_today", clear_today))

    # IMPORTANT: boss handler first, then group watcher
    app.add_handler(
        MessageHandler(
            filters.ALL & filters.User(user_id=BOSS_ID),
            reply_to_group,
        ),
        group=0,
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            watch_messages,
        ),
        group=1,
    )

    # Button clicks
    app.add_handler(CallbackQueryHandler(button_handler))

    # Daily summary
    app.job_queue.run_daily(daily_summary, time=time(hour=21, minute=0))

    print("✅ Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
