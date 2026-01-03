import asyncio, random, string, aiohttp, os
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
    kb.button(text="🔄 Refresh Inbox")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- COMMANDS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "👋 **Welcome to Temp Mail Pro**\n\n"
        "I generate high-speed disposable emails. No need to open any websites—read everything right here!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # Using a high-speed stable domain
    domain = "fexpost.com" 
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{domain}"
    password = "password123"
    
    # 1. Create account
    res = await call_api("/accounts", "POST", {"address": email, "password": password})
    
    # 2. Get Token
    tk = await call_api("/token", "POST", {"address": email, "password": password})
    
    if tk and 'token' in tk:
        USER_DATA[m.from_user.id] = {"email": email, "token": tk['token']}
        await m.answer(
            f"✅ **New temporary email generated:**\n\n"
            f"📧 `{email}`\n\n"
            f"**Tap the email to copy it.** Use it anywhere. When you get a mail, click 'Refresh Inbox' below.",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )
    else:
        await m.answer("❌ Mail server is currently busy. Please try again in 5 seconds.")

@dp.message(F.text == "🔄 Refresh Inbox")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_DATA:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    data = USER_DATA[user_id]
    status = await m.answer("🔍 **Checking for new messages...**", parse_mode="Markdown")
    
    messages = await call_api("/messages", token=data['token'])
    
    if not messages or not messages.get('hydra:member'):
        await status.edit_text(
            f"📧 **Address:** `{data['email']}`\n\n"
            f"**Your inbox is empty 📭**\n"
            f"Waiting for new emails...",
            parse_mode="Markdown"
        )
    else:
        await status.delete()
        for msg_item in messages['hydra:member'][:3]: # Show last 3 emails
            detail = await call_api(f"/messages/{msg_item['id']}", token=data['token'])
            
            # Extract plain text content
            body = detail.get('text', 'No text content found.')
            
            await m.answer(
                f"📩 **NEW MESSAGE RECEIVED**\n\n"
                f"👤 **From:** `{msg_item['from']['address']}`\n"
                f"📝 **Subject:** {msg_item['subject']}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"{body[:3000]}\n\n"
                f"━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
