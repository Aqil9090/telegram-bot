import os
from fastapi import FastAPI, Request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Get environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Your bot token from Render environment variables
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Your channel ID (e.g., "@mychannel" or "-1001234567890")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mysecret")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing! Set it in Render environment variables.")

# Create bot & app
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
fastapi_app = FastAPI()

# Keyboard layout
keyboard = [["Option 1", "Option 2", "Option 3"]]
reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a photo and I'll send it to the channel.", reply_markup=reply_markup)

# Handle photo messages
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    caption = update.message.caption or ""
    photo = update.message.photo[-1].file_id

    # Forward photo to the channel
    await bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=caption)

    # Reply to the user with the keyboard
    await update.message.reply_text("Photo received! Choose an option:", reply_markup=reply_markup)

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Webhook endpoint
@fastapi_app.post(f"/webhook/{WEBHOOK_SECRET}")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.initialize()
    await application.process_update(update)
    return {"status": "ok"}

# Root endpoint for testing
@fastapi_app.get("/")
def home():
    return {"status": "Bot is running with webhook!"}

# Run locally (for testing only)
if name == "main":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
