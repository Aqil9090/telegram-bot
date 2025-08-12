import os
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI, Request
import uvicorn

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002825102359")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mysecret")
RENDER_URL = os.getenv("RENDER_URL")  # e.g. https://mybot.onrender.com

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing!")

# Timezone
local_tz = pytz.timezone("Asia/Singapore")

# FastAPI app
fastapi_app = FastAPI()
bot_app = Application.builder().token(TOKEN).build()

# Keyboard function
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

# Handle button presses
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

# Register handlers
bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
bot_app.add_handler(CallbackQueryHandler(button_callback))

# Webhook endpoint
@fastapi_app.post(f"/webhook/{WEBHOOK_SECRET}")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

# Root endpoint
@fastapi_app.get("/")
async def home():
    return {"status": "Bot is running with webhook!"}

# Startup event → set webhook
@fastapi_app.on_event("startup")
async def on_startup():
    webhook_url = f"{RENDER_URL}/webhook/{WEBHOOK_SECRET}"
    await bot_app.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to {webhook_url}")

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
