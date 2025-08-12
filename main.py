import os
import asyncio
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Get environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Your bot token from Render environment variables
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Your channel ID (e.g., "@mychannel" or "-1001234567890")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing! Set it in Render environment variables.")

# Keyboard layout (same as your original)
keyboard = [["Option 1", "Option 2", "Option 3"]]
reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a photo and I'll send it to the channel.",
        reply_markup=reply_markup
    )

# Handle photo messages
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    caption = update.message.caption or ""
    photo = update.message.photo[-1].file_id

    # Forward photo to the channel
    await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=caption)

    # Reply to the user with the keyboard
    await update.message.reply_text(
        "Photo received! Choose an option:",
        reply_markup=reply_markup
    )

async def main():
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Start polling (no webhook needed)
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
