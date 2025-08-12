from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import datetime
import pytz
from fastapi import FastAPI
from threading import Thread
import uvicorn
import os

# --- BOT CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")  # Store your bot token in Render's Environment Variables
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002825102359")  # Your channel ID (-100...)

# Timezone
local_tz = pytz.timezone("Asia/Singapore")

# --- FastAPI for health check ---
app = FastAPI()

@app.get("/")
def root():
    return {"status": "Bot is running on Render!"}

@app.get("/ping")
def ping():
    return {"ping": "I'm alive"}

# --- Run FastAPI ---
def run_web():
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT env variable
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

# --- Multiple choice keyboard ---
def get_compliance_keyboard(selected):
    options = [
        "Tiada Suntikan Anti-Tifoid",
        "Tiada Sijil Pengendalian Makanan",
        "Tiada Apron",
        "Tiada Kasut",
        "Tiada Topi",
        "Tiada lesen/permit"
    ]
    kb = [[InlineKeyboardButton(opt + (" ✔" if opt in selected else ""), callback_data=opt)] for opt in options]
    kb.append([InlineKeyboardButton("Hantar", callback_data="Hantar")])
    return InlineKeyboardMarkup(kb)

# --- Handle photo uploads ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    photo = update.message.photo[-1].file_id
    caption = update.message.caption or "No remarks"
    timestamp = datetime.datetime.now(local_tz).strftime("%Y-%m-%d %H:%M:%S")

    context.user_data['pending_log'] = {
        'file_id': photo,
        'caption': caption,
        'timestamp': timestamp,
        'nick': user.first_name,
        'selections': []
    }

    await update.message.reply_text(
        "Sila pilih sebab ketidakpatuhan (boleh pilih lebih dari satu), kemudian tekan Hantar:",
        reply_markup=get_compliance_keyboard([])
    )

# --- Handle inline button clicks ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    pend = context.user_data.get('pending_log', {})
    sels = pend.get('selections', [])

    if data == "Hantar":
        if not sels:
            await query.edit_message_text("Tiada sebab dipilih. Sila pilih sekurang-kurangnya satu.")
            return

        text = (
            f"🕒 {pend['timestamp']}\n"
            f"👤 {pend['nick']}\n"
            f"💬 Catatan: {pend['caption']}\n"
            f"❗ Sebab Ketidakpatuhan: {', '.join(sels)}"
        )

        # Send to channel
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=pend['file_id'], caption=text)

        await query.edit_message_text("Log direkodkan ✅")
        context.user_data.pop('pending_log', None)

    else:
        if data in sels:
            sels.remove(data)
        else:
            sels.append(data)

        pend['selections'] = sels
        await query.edit_message_reply_markup(reply_markup=get_compliance_keyboard(sels))

# --- Start bot + server ---
def main():
    # Start web server in a separate thread
    Thread(target=run_web, daemon=True).start()
    print("FastAPI server started.")

    if not TOKEN:
        print("Error: BOT_TOKEN not set!")
        return

    try:
        print("Starting Telegram bot...")
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(CallbackQueryHandler(button_callback))

        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        print(f"Bot error: {e}")

if __name__ == "__main__":
    main()
