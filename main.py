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

# Multi-user storage
USER_DATA = {} 

# Domains available in 1secmail
DOMAINS = ["1secmail.com", "1secmail.org", "1secmail.net", "kzbat.com", "vjuum.com", "vps93.com", "firemail.cc", "testmail.help"]

# --- API HELPER ---
async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as r:
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
        "👋 **Welcome to Temp Mail Pro**\n\n"
        "Use the buttons below to manage your temporary email addresses.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # 1. Fast Random Address Generation
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    domain = random.choice(DOMAINS)
    email = f"{user}@{domain}"
    
    # 2. Save for the user
    USER_DATA[m.from_user.id] = {"email": email, "user": user, "domain": domain}
    
    # 3. UI exactly like the screenshot
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=f"https://www.1secmail.com/"))
    
    await m.answer(
        f"Your old email address has been successfully deleted\n\n"
        f"New temporary email address generated:\n\n"
        f"**{email}**",
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
    api_url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
    
    messages = await fetch_json(api_url)
    
    if not messages:
        # Show empty inbox UI
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=f"https://www.1secmail.com/"))
        await m.answer(
            f"Current email address: **{data['email']}**\n\n"
            f"Your inbox is empty",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Show the latest email
        latest = messages[0]
        # Fetch full message body
        msg_id = latest['id']
        body_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={msg_id}"
        full_msg = await fetch_json(body_url)
        
        content = full_msg.get('textBody', 'No content')
        await m.answer(
            f"📩 **New email message**\n\n"
            f"**From:** `{latest['from']}`\n"
            f"**Subject:** {latest['subject']}\n"
            f"**Date:** {latest['date']}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{content[:3000]}",
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
