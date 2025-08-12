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
import asyncio

# Your Telegram Bot Token (set in Render Environment Variables)
TOKEN = os.getenv("BOT_TOKEN")

# Your Telegram channel/chat ID
CHANNEL_ID = "-1002825102359"

# Timezone
local_tz = pytz.timezone("Asia/Singapore")

# FastAPI app for health check
app = FastAPI()

@app.get("/")
def root():
    return {"status": "Bot is running!"}

@app.get("/ping")
def ping():
    return {"ping": "I'm alive"}

# Start FastAPI server in a thread
def run_web():
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Keyboard generator
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

# Handle photo messages
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

# Handle button interactions
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
            f"❗Sebab Ketidakpatuhan: {', '.join(sels)}"
        )

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

# Main function
async def main():
    # Start FastAPI server
    Thread(target=run_web, daemon=True).start()

    application = ApplicationBuilder().token(TOKEN).build()

    # Auto delete webhook before starting polling
    await application.bot.delete_webhook(drop_pending_updates=True)

    # Add handlers
    application.
