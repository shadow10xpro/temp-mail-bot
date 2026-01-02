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
API_URL = "https://api.mail.tm"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- HELPERS ---
async def call_api(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, f"{API_URL}{url}", json=data, headers=headers, timeout=5) as r:
                return await r.json()
        except: return None

def get_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- COMMANDS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "👋 **Welcome to Temp Mail Pro**\n\nUse the buttons below to manage your temporary email addresses.",
        reply_markup=get_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def fast_gen(m: types.Message):
    status_msg = await m.answer("⚡ *Generating...*", parse_mode="Markdown")
    
    # Fast domain fetch
    doms = await call_api("/domains")
    if not doms or 'hydra:member' not in doms:
        await status_msg.edit_text("❌ Server busy. Try again.")
        return

    # Pick a random domain from all available ones
    domain = random.choice(doms['hydra:member'])['domain']
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    addr = f"{user}@{domain}"
    pwd = "pass" + ''.join(random.choices(string.digits, k=5))
    
    # Create and Get Token quickly
    await call_api("/accounts", "POST", {"address": addr, "password": pwd})
    tk_res = await call_api("/token", "POST", {"address": addr, "password": pwd})
    
    if tk_res and 'token' in tk_res:
        token = tk_res['token']
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🌐 Open in Browser", url="https://mail.tm/"))
        
        await status_msg.delete() # Remove the "Generating" text
        await m.answer(
            f"✅ **New temporary email address generated:**\n\n"
            f"📧 `{addr}`\n\n"
            f"Your old address (if any) has been replaced.",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        # Store token in a hidden way (for this session)
        # In a real bot, you'd use a database, but for speed, we use this:
        dp["last_token"] = token 
    else:
        await status_msg.edit_text("❌ Failed to generate. Try again.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    token = dp.get("last_token")
    if not token:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    res = await call_api("/messages", token=token)
    if not res or not res.get('hydra:member'):
        await m.answer(f"📧 **Current email address:**\nChecking inbox... \n\n**Your inbox is empty**", parse_mode="Markdown")
    else:
        msg_data = res['hydra:member'][0]
        await m.answer(
            f"📩 **New email message**\n\n"
            f"**From:** `{msg_data['from']['address']}`\n"
            f"**Subject:** {msg_data['subject']}\n\n"
            f"_{msg_data['intro']}_",
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
