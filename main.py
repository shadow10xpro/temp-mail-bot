import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import WebAppInfo
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Official Bot Live"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT SETUP ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

async def call_api(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, f"https://api.mail.tm{url}", json=data, headers=headers, timeout=15) as r:
                return await r.json()
        except: return None

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "👋 **Welcome to Temp Mail Official**\n\n"
        "I provide high-speed disposable emails. My domains are rarely blocked, so you will receive your OTPs instantly.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("🚀 **Generating official inbox...**")
    
    # 1. Get Domain
    doms = await call_api("/domains")
    if not doms or 'hydra:member' not in doms:
        await status.edit_text("❌ Server busy. Please try again.")
        return
    
    domain = doms['hydra:member'][0]['domain']
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email, pwd = f"{user}@{domain}", "pass12345"
    
    # 2. Create Account
    await call_api("/accounts", "POST", {"address": email, "password": pwd})
    
    # 3. Get Token
    tk = await call_api("/token", "POST", {"address": email, "password": pwd})
    
    if tk and 'token' in tk:
        USER_DATA[m.from_user.id] = {"email": email, "token": tk['token']}
        
        builder = InlineKeyboardBuilder()
        # --- THE PRO FIX: WEB APP ---
        # This opens the inbox smoothly INSIDE Telegram
        builder.row(types.InlineKeyboardButton(
            text="📥 Open Inbox (Smooth)", 
            web_app=WebAppInfo(url="https://mail.tm/en/")
        ))
        
        await status.delete()
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"📧 **{email}**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await status.edit_text("❌ Server rejected request. Please try again.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_DATA:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    data = USER_DATA[user_id]
    
    # Check for messages
    messages = await call_api("/messages", token=data['token'])
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📥 Open Full Inbox", web_app=WebAppInfo(url="https://mail.tm/en/")))

    if not messages or not messages.get('hydra:member'):
        await m.answer(
            f"Current email address:\n**{data['email']}**\n\n"
            f"**Your inbox is empty**\n"
            f"Waiting for incoming emails...",
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
            f"📩 **New Message Received!**\n\n"
            f"👤 **From:** `{msg_item['from']['address']}`\n"
            f"📝 **Subject:** {msg_item['subject']}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{body[:3000]}",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
