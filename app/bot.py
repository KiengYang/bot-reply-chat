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
# app.config should define:
# BOT_TOKEN, BOSS_ID, ALERT_GROUP_ID, TRIGGERS_TO_BOSS, TRIGGERS_TO_GROUP

from app.config import (
    BOT_TOKEN,
    BOSS_ID,
    ALERT_GROUP_ID,
    TRIGGERS_TO_BOSS,
    TRIGGERS_TO_GROUP,
    ROUTES,
)


DB_FILE = "app/db.json"

# key = user_id (boss or alert group admin), value = message key in DB
reply_map = {}
last_triggered_users = {}

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
    """Boss can type /summary to see pending & ignored messages in a clean format."""
    db = load_db()
    pending = []
    ignored = []

    for entry in db.values():
        status = entry.get("status")
        if status == "pending":
            pending.append(entry)
        elif status == "ignored":
            ignored.append(entry)

    if not pending and not ignored:
        await update.message.reply_text(
            "📊 No pending or ignored messages.",
            parse_mode="Markdown",
        )
        return

    def build_section(title, items):
        if not items:
            return f"*{title}*\n_No messages._\n\n"

        try:
            items.sort(key=lambda e: datetime.fromisoformat(e["time"]))
        except Exception:
            pass

        text = f"*{title}*\n"
        for e in items:
            try:
                dt = datetime.fromisoformat(e["time"])
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = e.get("time", "Unknown time")

            group_title = e.get("group_title", "group")
            sender = e.get("sender", "Unknown")
            preview = (e.get("text") or "").replace("\n", " ")[:80]

            group_username = e.get("group_username")
            group_id = e.get("group_id")
            message_id = e.get("message_id")

            if group_username:
                open_link = f"tg://resolve?domain={group_username}&post={message_id}"
            elif str(group_id).startswith("-100"):
                chat_id_for_link = str(group_id)[4:]
                open_link = f"https://t.me/c/{chat_id_for_link}/{message_id}"
            else:
                open_link = f"Message ID: `{message_id}`"

            text += (
                f"- `[{time_str}]` *{group_title}* — *{sender}*\n"
                f"  {preview}...\n"
            )

            if open_link.startswith("http") or open_link.startswith("tg://"):
                text += f"  [Open message]({open_link})\n\n"
            else:
                text += f"  {open_link}\n\n"

        return text

    msg = "📊 *Summary — Pending & Ignored Messages*\n\n"
    msg += build_section("⏳ Pending", pending)
    msg += build_section("🚫 Ignored", ignored)


    MAX_LEN = 4000  # a bit under Telegram's 4096 limit

    if len(msg) > MAX_LEN:
        msg = msg[:MAX_LEN - 50] + "\n\n... truncated, too many items."

    await update.message.reply_text(
        msg,
        disable_web_page_preview=True,
    )



async def clear_today(update, context: ContextTypes.DEFAULT_TYPE):
    """Clear today's pending & ignored messages from the database."""
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

        try:
            dt = datetime.fromisoformat(t_str) if t_str else None
        except Exception:
            dt = None

        is_today = dt is not None and dt.date() == today
        is_target_status = status in ("pending", "ignored")

        if is_today and is_target_status:
            removed += 1
            continue

        new_db[key] = entry

    save_db(new_db)

    if removed == 0:
        await update.message.reply_text(
            "🧹 No pending or ignored messages for today to clear."
        )
    else:
        await update.message.reply_text(
            f"🧹 Cleared {removed} pending/ignored messages for today."
        )

# ------------------- summary clear (GROUPS) -------------------

async def clear_all(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOSS_ID:
        return  # only boss can clear

    db = load_db()
    count = len(db)
    db.clear()
    save_db(db)

    await update.message.reply_text(f"🧹 Cleared ALL {count} stored alerts.")

# ------------------- MESSAGE WATCHER (GROUPS) -------------------

async def watch_messages(update, context: ContextTypes.DEFAULT_TYPE):
    """
    Detect trigger words or boss mentions in groups.
    Some triggers route via ROUTES, others use legacy boss/group logic.
    """
    if not update.message or not update.message.text:
        return
    if update.message.chat.type not in ("group", "supergroup"):
        return

    text = update.message.text.lower()
    print("New message:", text)
    print("Chat info:", update.message.chat)

    text = update.message.text.lower()
    trigger_word = None
    # ---------- 1) ROUTES-BASED TRIGGERS ----------
    route = None
    for word, info in ROUTES.items():
        if word in text:
            route = info
            trigger_word = word
            break

    # ---------- 2) LEGACY TRIGGERS (fallback) ----------
    triggered_to_boss = False
    triggered_to_group = False

    for word in TRIGGERS_TO_BOSS:
        if word.lower() in text:
            triggered_to_boss = True
            trigger_word = word
            break

    if not triggered_to_boss:
        for word in TRIGGERS_TO_GROUP:
            if word.lower() in text:
                triggered_to_group = True
                trigger_word = word
                break

    # Direct mention of boss username -> force boss
    if update.message.entities:
        for entity in update.message.entities:
            if (
                entity.type == "mention"
                and "@kiengyang" in update.message.text.lower()
            ):
                triggered_to_boss = True
                triggered_to_group = False
                break

    # Nothing triggered at all -> stop
    if route is None and not triggered_to_boss and not triggered_to_group:
        return

    # ---------- 3) DECIDE DESTINATION ----------
    if route is not None:
        dest_chat_id = route["boss_chat"]
        thread_id = route.get("thread_id")
    else:
        thread_id = None
        if triggered_to_boss:
            dest_chat_id = BOSS_ID
        else:
            dest_chat_id = ALERT_GROUP_ID

    # Track trigger user for later voice forwarding
    chat_id = update.message.chat.id
    last_triggered_users[chat_id] = (
        update.message.from_user.id,
        datetime.now(),
        dest_chat_id,
    )
    print(f"Tracked trigger: {update.message.from_user.full_name} in {chat_id}")

    mentions = []
    if route is not None:
        mentions = route.get("mentions", [])
    mention_line = ", ".join(mentions) if mentions else "N/A"

    # ---------- 4) SAVE MESSAGE INFO ----------
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

    # ---------- 5) BUILD BUTTONS ----------
    open_url = None
    chat_id_str = str(update.message.chat.id)

    if update.message.chat.username:
        open_url = (
            f"tg://resolve?domain={update.message.chat.username}"
            f"&post={update.message.message_id}"
    )
    elif chat_id_str.startswith("-100"):
        chat_id_for_link = chat_id_str[4:]
        open_url = f"https://t.me/c/{chat_id_for_link}/{update.message.message_id}"
    else:
        print("No open_url for this chat (ChatType.GROUP).")
    buttons = []

# Open in group button (keep as is if you like)
    if open_url:
        buttons.append([InlineKeyboardButton("Open in group", url=open_url)])

# Status toggle button
    buttons.append(
        [InlineKeyboardButton("Mark as replied", callback_data=f"toggle|{key}")]
    )

# Keep Ignore button
    buttons.append(
        [InlineKeyboardButton("Ignore", callback_data=f"ignore|{key}")]
    )

    kb = InlineKeyboardMarkup(buttons)


    # ---------- 6) SEND ALERT ----------
    await context.bot.send_message(
        chat_id=dest_chat_id,
        text=(
            f"📣 Dear Mr. {mention_line}\n"
            f"👤 From: {update.message.from_user.full_name}\n"
            f"🎯 Group: {update.message.chat.title}\n"
            f"💡 Keyword: \"{trigger_word or 'N/A'}\"\n"
            f"Please Mr. {mention_line}, kindly check and reply.\n"
            f"✉️ For more details, please see below 👇\n {update.message.text}"
        ),
        reply_markup=kb,
        message_thread_id=thread_id,
    )

    print(f"Forwarded message {key} to {dest_chat_id} with buttons.")


# ------------------- VOICE WACHTER -------------------

async def watch_voice(update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return
    if update.message.chat.type not in ("group", "supergroup"):
        return

    chat_id = update.message.chat.id
    if chat_id not in last_triggered_users:
        return

    trigger_user_id, trigger_time, dest_chat_id = last_triggered_users[chat_id]

    if update.message.from_user.id != trigger_user_id:
        return

    time_diff = (datetime.now() - trigger_time).total_seconds()
    if time_diff > 60:
        return

    await update.message.forward(dest_chat_id)
    print(f"✅ Voice forwarded ({time_diff:.0f}s after trigger)")

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
        # Use the user who pressed the button as the reply owner (usually boss)
        reply_map[query.from_user.id] = key
        print(f"Reply mode ON for user={query.from_user.id}, key={key}")
        await query.edit_message_text(
            "✏️ Reply mode activated. Send your reply below in this private chat and it will be forwarded to the group automatically."
        )

    if action == "toggle":
        db[key]["status"] = "replied"
        save_db(db)
        await query.edit_message_text("✅ Marked as replied.")
        return

# ------------------- REPLY HANDLER -------------------
async def reply_to_group(update, context: ContextTypes.DEFAULT_TYPE):
    """
    Forward reply (from boss or whoever clicked Reply) to the original group
    as a forwarded message.
    """
    if not update.message:
        return

    user_id = update.effective_user.id

    # Only handle replies from users who are in reply_map
    if user_id not in reply_map:
        print("Message from user without active reply_map -> ignore.")
        return

    print("Reply user sent:", update.message)
    print("Reply user chat info:", update.message.chat)

    key = reply_map[user_id]
    db = load_db()

    if key not in db:
        await update.message.reply_text("❌ Original message expired.")
        del reply_map[user_id]
        return

    entry = db[key]
    print("reply_to_group triggered")
    print("Forwarding reply message")
    print("Target chat_id:", entry["group_id"], "message_id:", entry["message_id"])

    # Forward the user's message (text, voice, photo, etc.) to the original group
    await update.message.forward(chat_id=entry["group_id"])

    db[key]["status"] = "replied"
    save_db(db)

    await update.message.reply_text("✅ Your reply has been forwarded to the group.")
    del reply_map[user_id]
    print(f"Reply mode OFF for user={user_id}")


# ------------------- DAILY SUMMARY -------------------
async def daily_summary(job):
    """Send daily summary of pending and ignored messages, with timestamps."""
    db = load_db()

    pending = []
    ignored = []

    for entry in db.values():
        status = entry.get("status")
        if status == "pending":
            pending.append(entry)
        elif status == "ignored":
            ignored.append(entry)

    if not pending and not ignored:
        await job.bot.send_message(BOSS_ID, "📊 No pending or ignored messages today.")
        return

    def build_section(title, items):
        if not items:
            return f"*{title}*\n_No messages._\n\n"

        try:
            items.sort(key=lambda e: datetime.fromisoformat(e["time"]))
        except Exception:
            pass

        text = f"*{title}*\n"
        for e in items:
            try:
                dt = datetime.fromisoformat(e["time"])
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = e.get("time", "Unknown time")

            group_title = e.get("group_title", "group")
            sender = e.get("sender", "Unknown")
            preview = (e.get("text") or "").replace("\n", " ")[:80]

            group_username = e.get("group_username")
            group_id = e.get("group_id")
            message_id = e.get("message_id")

            if group_username:
                open_link = f"tg://resolve?domain={group_username}&post={message_id}"
            elif str(group_id).startswith("-100"):
                chat_id_for_link = str(group_id)[4:]
                open_link = f"https://t.me/c/{chat_id_for_link}/{message_id}"
            else:
                open_link = f"Message ID: `{message_id}`"

            text += (
                f"- `[{time_str}]` *{group_title}* — *{sender}*\n"
                f"  {preview}...\n"
            )

            if open_link.startswith("http") or open_link.startswith("tg://"):
                text += f"  [Open message]({open_link})\n\n"
            else:
                text += f"  {open_link}\n\n"

        return text

    msg = "📊 *Daily Summary — Pending & Ignored Messages*\n\n"
    msg += build_section("⏳ Pending", pending)
    msg += build_section("🚫 Ignored", ignored)

    await job.bot.send_message(
        BOSS_ID,
        msg,
     #   parse_mode="Markdown",
        disable_web_page_preview=True,
    )

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
    app.add_handler(MessageHandler(filters.VOICE, watch_voice), group=2)

    app.add_handler(CommandHandler("clear_all", clear_all))
    # Replies from boss / whoever clicked Reply button
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            reply_to_group,
        ),
        group=0,
    )

    # Group watcher (must come after reply handler)
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
