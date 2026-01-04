import asyncio
import random
import string
import aiohttp
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT SETUP ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Multi-user storage to keep things fast
USER_DATA = {} 

# List of domains that are very fast
DOMAINS = ["1secmail.com", "1secmail.org", "1secmail.net", "kzbat.com", "vjuum.com", "vps93.com"]

# --- API HELPER ---
async def call_api(url):
    async with aiohttp.ClientSession() as session:
        try:
            # Using a real User-Agent to prevent "Forbidden" errors
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            async with session.get(url, headers=headers, timeout=10) as r:
                return await r.json()
        except: return None

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- COMMANDS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "👋 **Welcome to Temp Mail Official**\n\n"
        "I provide high-speed disposable emails with an official browser interface. Use the menu below.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # This part is instant and never "Busy"
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = random.choice(DOMAINS)
    email = f"{user}@{domain}"
    
    # Store user data
    USER_DATA[m.from_user.id] = {"email": email, "user": user, "domain": domain}
    
    # The "Secret" link that bypasses Forbidden errors and opens the mailbox directly
    mailbox_url = f"https://www.1secmail.com/mailbox/?login={user}&domain={domain}"
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=mailbox_url))
    
    await m.answer(
        f"Your old email address has been successfully deleted\n\n"
        f"New temporary email address generated:\n\n"
        f"📧 **{email}**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_DATA:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    data = USER_DATA[user_id]
    mailbox_url = f"https://www.1secmail.com/mailbox/?login={data['user']}&domain={data['domain']}"
    
    # Check for messages via API so the user can see them in Telegram too
    api_url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
    messages = await call_api(api_url)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=mailbox_url))

    if not messages:
        await m.answer(
            f"Current email address:\n**{data['email']}**\n\n"
            f"**Your inbox is empty**\n"
            f"Waiting for incoming emails...",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # If there's a new mail, show the sender and subject
        msg = messages[0]
        await m.answer(
            f"📩 **New Message Found!**\n\n"
            f"👤 **From:** `{msg['from']}`\n"
            f"📝 **Subject:** {msg['subject']}\n\n"
            f"💡 _Click 'Open in Browser' to read the full content and see attachments._",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
