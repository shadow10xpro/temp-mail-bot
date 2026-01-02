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

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://api.mail.tm"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Memory to store user data (This keeps it fast)
USER_STORAGE = {} 
CACHED_DOMAINS = []

# --- HELPERS ---
async def call_api(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, f"{API_URL}{url}", json=data, headers=headers, timeout=15) as r:
                if r.status > 400: return None
                return await r.json()
        except: return None

async def get_domains():
    global CACHED_DOMAINS
    res = await call_api("/domains")
    if res and 'hydra:member' in res:
        CACHED_DOMAINS = [d['domain'] for d in res['hydra:member']]

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- LOGIC ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("👋 **Welcome!**\n\nUse the buttons below to generate a new email or check your inbox.", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # Ensure we have domains
    if not CACHED_DOMAINS:
        await get_domains()
    
    if not CACHED_DOMAINS:
        await m.answer("❌ Mail server is currently slow. Please try again in 5 seconds.")
        return

    # 1. Prepare Details
    domain = random.choice(CACHED_DOMAINS)
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    addr = f"{user}@{domain}"
    pwd = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    # 2. Create Account
    acc = await call_api("/accounts", "POST", {"address": addr, "password": pwd})
    if not acc:
        # Retry once with different username if server rejected
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        addr = f"{user}@{domain}"
        acc = await call_api("/accounts", "POST", {"address": addr, "password": pwd})

    # 3. Get Token
    tk_res = await call_api("/token", "POST", {"address": addr, "password": pwd})
    
    if tk_res and 'token' in tk_res:
        token = tk_res['token']
        # Save to memory
        USER_STORAGE[m.from_user.id] = {"address": addr, "token": token}
        
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=f"https://mail.tm/"))
        
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"**{addr}**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await m.answer("❌ Server busy. Please tap 'Generate' again.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_STORAGE:
        await m.answer("❌ No active email found. Click 'Generate' first.")
        return

    data = USER_STORAGE[user_id]
    res = await call_api("/messages", token=data['token'])
    
    if not res or 'hydra:member' not in res or not res['hydra:member']:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=f"https://mail.tm/"))
        await m.answer(
            f"Current email address:\n**{data['address']}**\n\n"
            f"Your inbox is empty",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # Show the most recent email
        msg = res['hydra:member'][0]
        full_msg = await call_api(f"/messages/{msg['id']}", token=data['token'])
        content = full_msg.get('text', 'No content')
        
        await m.answer(
            f"📩 **New email message**\n\n"
            f"**From:** {msg['from']['address']}\n"
            f"**Subject:** {msg['subject']}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{content[:3500]}",
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    # Pre-fetch domains on start to save time later
    await get_domains()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
