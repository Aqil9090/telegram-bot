from fastapi import FastAPI, Request
import requests
import os

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Bot token from environment variable
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mysecret")

# Safety check to avoid silent failures
if not TOKEN:
    raise ValueError("BOT_TOKEN is not set. Please set it as an environment variable.")

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running!"}

@app.post(f"/webhook/{WEBHOOK_SECRET}")
async def webhook(request: Request):
    data = await request.json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text.lower() == "/start":
            send_message(chat_id, "Hello! Your bot is working on Render 🚀")
        else:
            send_message(chat_id, f"You said: {text}")

    return {"ok": True}

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)
