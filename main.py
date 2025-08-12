import os
import datetime
import pytz
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI
from threading import Thread
import uvicorn

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002825102359")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing!")

local_tz = pytz.timezone("Asia/Singapore")

# =========================
# LOGGING CONFIG
# =========================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =========================
# FASTAPI SERVER
# =========================
fastapi_app = FastAPI()

@fastapi_app.get("/")
def home():
    return {"status": "Bot is running!"}

@fastapi_app.get("/ping")
def ping():
    return {"ping": "I'm alive"}

def run_fastapi():
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)

# =========================
# KEYBOARD FUNCTION
# =========================
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

# =========================
# HANDLERS
# =========================
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

    logger.info(f"📸 Photo received from {user.first_name} at {timestamp} | Caption: {caption}")

    await update.message.reply_text(
        "Sila pilih sebab ketidakpatuhan (boleh pilih lebih dari satu), kemudian tekan Hantar:",
        reply_markup=get_compliance_keyboard([])
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    pend = context.user_data.get('pending_log', {})
    sels = pend.get('selections', [])

    logger.info(f"🔘 Button pressed: {data} | Current selections: {sels}")

    if data == "Hantar":
        if not sels:
            await query.edit_message_text("Tiada sebab dipilih. Sila pilih sekurang-kurangnya satu.")
            logger.warning("⚠️ Attempted to send with no selections.")
            return

        text = (
            f"🕒 {pend['timestamp']}\n"
            f"👤 {pend['nick']}\n"
            f"💬 Catatan: {pend['caption']}\n"
            f"❗Sebab Ketidakpatuhan: {', '.join(sels)}"
        )

        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=pend['file_id'], caption=text)
        await query.edit_message_text("Log direkodkan ✅")
        logger.info(f"✅ Log sent to channel {CHANNEL_ID} from {pend['nick']}")
        context.user_data.pop('pending_log', None)
    else:
        if data in sels:
            sels.remove(data)
        else:
            sels.append(data)

        pend['selections'] = sels
        await query.edit_message_reply_markup(reply_markup=get_compliance_keyboard(sels))

# =========================
# BOT RUNNER
# =========================
def main():
    # Start FastAPI
    Thread(target=run_fastapi, daemon=True).start()

    # Start polling bot
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("🚀 Bot started and polling for updates...")
    application.run_polling()

if __name__ == "__main__":
    main()
