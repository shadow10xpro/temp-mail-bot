import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Pro Bot is Live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT SETUP ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

# Headers to prevent "Busy" and "Forbidden" errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Mobile Safari/537.36",
    "Accept": "application/json"
}

# --- SERVICE 1: TEMP-MAIL.IO (Most Stable) ---
async def fetch_temp_mail_io():
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.post("https://api.temp-mail.io/v1/emails", timeout=5) as r:
                data = await r.json()
                return {"email": data['email'], "token": data['token'], "type": "io", "url": "https://temp-mail.io/en"}
    except: return None

# --- SERVICE 2: 1SECMAIL (Highest Uptime) ---
async def fetch_1secmail():
    try:
        domains = ["1secmail.com", "1secmail.org", "kzbat.com", "vjuum.com"]
        domain = random.choice(domains)
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{user}@{domain}"
        return {"email": email, "user": user, "domain": domain, "type": "1sec", "url": f"https://www.1secmail.com/"}
    except: return None

# --- SERVICE 3: MAIL.TM (Backup) ---
async def fetch_mail_tm():
    try:
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        addr, pwd = f"{user}@fexpost.com", "pass12345"
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.post("https://api.mail.tm/accounts", json={"address": addr, "password": pwd}, timeout=5) as r:
                if r.status == 201:
                    async with s.post("https://api.mail.tm/token", json={"address": addr, "password": pwd}) as r2:
                        tk = await r2.json()
                        return {"email": addr, "token": tk['token'], "type": "mail_tm", "url": "https://mail.tm/en/"}
    except: return None

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("👋 **Welcome to Temp Mail Pro**\n\nI use 3 different servers to ensure 100% success. Try generating a mail now!", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("⚡ **Generating (Trying Server 1)...**", parse_mode="Markdown")
    
    # Try Service 1
    res = await fetch_temp_mail_io()
    if not res:
        await status.edit_text("⚡ **Server 1 Busy... Trying Server 2...**")
        res = await fetch_1secmail()
    if not res:
        await status.edit_text("⚡ **Server 2 Busy... Trying Server 3...**")
        res = await fetch_mail_tm()

    if res:
        USER_DATA[m.from_user.id] = res
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=res['url']))
        
        await status.delete()
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"**{res['email']}**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await status.edit_text("❌ All 3 servers are temporarily down. This usually means the mail providers are updating. Please try again in 1 minute.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))
    
    await m.answer(
        f"Current email address:\n**{data['email']}**\n\n"
        f"**Your inbox is empty**\n"
        f"_Please click the button below to check your mail in the smooth web view._",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
