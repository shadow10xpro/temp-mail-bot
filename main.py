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

# --- API HELPER ---
async def call_api(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, f"https://api.mail.tm{url}", json=data, headers=headers, timeout=10) as r:
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
    # Use a common stable domain to make it INSTANT
    domain = "fexpost.com" 
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{domain}"
    password = "password123"
    
    # 1. Create account (Fast)
    await call_api("/accounts", "POST", {"address": email, "password": password})
    
    # 2. Get Token
    tk = await call_api("/token", "POST", {"address": email, "password": password})
    
    if tk and 'token' in tk:
        USER_DATA[m.from_user.id] = {"email": email, "token": tk['token']}
        
        builder = InlineKeyboardBuilder()
        # This link is beautiful and works on all phones
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url="https://mail.tm/en/"))
        
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"**{email}**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await m.answer("❌ Server is tight. Please try again in a moment.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_DATA:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    data = USER_DATA[user_id]
    messages = await call_api("/messages", token=data['token'])
    
    if not messages or not messages.get('hydra:member'):
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url="https://mail.tm/en/"))
        await m.answer(
            f"Current email address: **{data['email']}**\n\n"
            f"Your inbox is empty",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Get the latest message
        msg_item = messages['hydra:member'][0]
        # Get full content
        detail = await call_api(f"/messages/{msg_item['id']}", token=data['token'])
        
        body = detail.get('text', 'No text content')
        await m.answer(
            f"📩 **New email message**\n\n"
            f"**From:** `{msg_item['from']['address']}`\n"
            f"**Subject:** {msg_item['subject']}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{body[:3000]}",
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
