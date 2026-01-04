import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Official Bot is Live"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT SETUP ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

# --- PROFESSIONAL HEADERS (Stops "Busy" errors) ---
def get_headers():
    return {
        "User-Agent": random.choice([
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
        ]),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

# --- SERVICE 1: 1SECMAIL (Fastest & Never Busy) ---
async def fetch_1secmail():
    try:
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        domain = random.choice(["1secmail.com", "1secmail.org", "kzbat.com", "vjuum.com"])
        email = f"{user}@{domain}"
        # Direct mailbox link that works on mobile
        url = f"https://www.1secmail.com/mailbox/?login={user}&domain={domain}"
        return {"email": email, "user": user, "domain": domain, "type": "1sec", "url": url}
    except: return None

# --- SERVICE 2: MAIL.TM (Backup with spoofed headers) ---
async def fetch_mail_tm():
    try:
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email, pwd = f"{user}@fexpost.com", "pass12345"
        async with aiohttp.ClientSession(headers=get_headers()) as s:
            async with s.post("https://api.mail.tm/accounts", json={"address": email, "password": pwd}, timeout=5) as r:
                if r.status == 201:
                    async with s.post("https://api.mail.tm/token", json={"address": email, "password": pwd}) as r2:
                        tk = await r2.json()
                        return {"email": email, "token": tk['token'], "type": "tm", "url": "https://mail.tm/en/"}
    except: return None

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- BOT ACTIONS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "👋 **Welcome to Temp Mail Pro**\n\n"
        "I provide high-speed disposable emails. Use the buttons below.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("🚀 **Generating official email...**")
    
    # SMART FAILOVER: 1secmail is used first because it's never busy on Render
    res = await fetch_1secmail()
    if not res:
        res = await fetch_mail_tm()

    if res:
        USER_DATA[m.from_user.id] = res
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=res['url']))
        
        await status.delete()
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"📧 **{res['email']}**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await status.edit_text("❌ All servers are busy. Please try again in 5 seconds.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))
    
    # If it's a 1secmail, we check for OTP in the bot too
    if data['type'] == "1sec":
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                msgs = await r.json()
                if msgs:
                    m_id = msgs[0]['id']
                    url2 = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={m_id}"
                    async with s.get(url2) as r2:
                        det = await r2.json()
                        await m.answer(f"📩 **New Message!**\n\n**From:** {det['from']}\n**Subject:** {det['subject']}\n\n{det['textBody'][:3000]}", reply_markup=builder.as_markup(), parse_mode="Markdown")
                        return

    await m.answer(
        f"Current email address:\n**{data['email']}**\n\n"
        f"**Your inbox is empty**\n"
        f"Waiting for incoming emails...",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
