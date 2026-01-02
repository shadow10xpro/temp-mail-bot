import asyncio
import random
import string
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
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

async def call_api(url, method="GET", data=None, token=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(method, f"{API_URL}{url}", json=data, headers=headers, timeout=10) as r:
                return await r.json()
        except Exception as e:
            return {"error": str(e)}

@dp.message(Command("start"))
async def start(m: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📧 Generate New Email", callback_data="gen"))
    await m.answer(f"🚀 **Temp Mail Pro**\n\nTap the button below to get a disposable email address instantly.", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "gen")
async def gen(c: types.CallbackQuery):
    msg = await c.message.edit_text("🔍 **Searching for available domains...**")
    
    # 1. Get Domains
    doms = await call_api("/domains")
    if "hydra:member" not in doms or not doms['hydra:member']:
        await msg.edit_text("❌ Error: Could not find mail domains. Try again in a minute.")
        return

    domain = doms['hydra:member'][0]['domain']
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    addr = f"{user}@{domain}"
    pwd = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    
    await msg.edit_text("✨ **Creating your private inbox...**")

    # 2. Create Account
    acc = await call_api("/accounts", "POST", {"address": addr, "password": pwd})
    if "error" in acc or "id" not in acc:
        await msg.edit_text(f"❌ Account creation failed. Please try again.")
        return

    # 3. Get Token
    tk_res = await call_api("/token", "POST", {"address": addr, "password": pwd})
    token = tk_res.get('token')

    if not token:
        await msg.edit_text("❌ Login failed. The mail server is busy.")
        return

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📥 Refresh Inbox", callback_data=f"ref_{token}"))
    
    await msg.edit_text(
        f"✅ **Your Temp Email is Ready!**\n\n"
        f"📧 `{addr}`\n"
        f"🔑 `{pwd}`\n\n"
        f"💡 *Tip:* Tap the email address to copy it. Use it anywhere you need to sign up!",
        reply_markup=kb.as_markup(), 
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("ref_"))
async def ref(c: types.CallbackQuery):
    token = c.data.split("_")[1]
    await c.answer("Checking for new messages...")
    
    mails = await call_api("/messages", token=token)
    if "hydra:member" not in mails or not mails['hydra:member']:
        await c.answer("Inbox is empty. No emails yet! 📬", show_alert=True)
    else:
        m = mails['hydra:member'][0]
        # Get full message content
        details = await call_api(f"/messages/{m['id']}", token=token)
        text_content = details.get('text', 'No content')
        
        await c.message.answer(
            f"📩 **New Message!**\n\n"
            f"👤 **From:** {m['from']['address']}\n"
            f"📝 **Subject:** {m['subject']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{text_content[:3000]}", # Show up to 3000 chars
            parse_mode="Markdown"
        )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
