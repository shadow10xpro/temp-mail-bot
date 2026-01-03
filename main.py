import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import WebAppInfo
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Hybrid Bot is Live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

# --- API HANDLERS ---
async def try_mail_tm():
    """Service 1: Mail.tm (Best Quality)"""
    try:
        domain = "fexpost.com"
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email, pwd = f"{user}@{domain}", "pass12345"
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.mail.tm/accounts", json={"address": email, "password": pwd}, timeout=3) as r1:
                if r1.status == 201:
                    async with s.post("https://api.mail.tm/token", json={"address": email, "password": pwd}) as r2:
                        res = await r2.json()
                        return {"email": email, "token": res['token'], "type": "mail.tm", "url": "https://mail.tm/en/"}
    except: return None

async def try_1secmail():
    """Service 2: 1secmail (Highest Speed)"""
    try:
        domains = ["1secmail.com", "1secmail.org", "kzbat.com"]
        domain = random.choice(domains)
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"{user}@{domain}"
        return {"email": email, "user": user, "domain": domain, "type": "1sec", "url": "https://www.1secmail.com/"}
    except: return None

# --- UI COMPONENTS ---
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- BOT LOGIC ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🚀 **Welcome to Temp Mail Pro (Hybrid)**\n\nI use multiple servers to ensure you always get an email instantly.", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # Fallover System: Try Mail.tm first, then 1secmail
    res = await try_mail_tm()
    if not res:
        res = await try_1secmail()
    
    if res:
        USER_DATA[m.from_user.id] = res
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", web_app=WebAppInfo(url=res['url'])))
        
        await m.answer(
            f"✅ **Temp Email Generated Successfully**\n\n"
            f"📧 `{res['email']}`\n\n"
            f"_Tap to copy. All messages appear below._",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await m.answer("❌ All mail servers are currently busy. Try again in 10 seconds.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ Please generate an email first.")
        return

    # Logic based on which provider the user has
    async with aiohttp.ClientSession() as s:
        if data['type'] == "mail.tm":
            headers = {"Authorization": f"Bearer {data['token']}"}
            async with s.get("https://api.mail.tm/messages", headers=headers) as r:
                msgs = await r.json()
                if not msgs.get('hydra:member'):
                    await m.answer(f"📧 `{data['email']}`\n\n**Inbox is empty**", parse_mode="Markdown")
                else:
                    m_id = msgs['hydra:member'][0]['id']
                    async with s.get(f"https://api.mail.tm/messages/{m_id}", headers=headers) as r2:
                        det = await r2.json()
                        await m.answer(f"📩 **New Mail**\n\n**From:** {det['from']['address']}\n**Subject:** {det['subject']}\n\n{det['text'][:3000]}", parse_mode="Markdown")
        
        elif data['type'] == "1sec":
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
            async with s.get(url) as r:
                msgs = await r.json()
                if not msgs:
                    await m.answer(f"📧 `{data['email']}`\n\n**Inbox is empty**", parse_mode="Markdown")
                else:
                    m_id = msgs[0]['id']
                    url2 = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={m_id}"
                    async with s.get(url2) as r2:
                        det = await r2.json()
                        await m.answer(f"📩 **New Mail**\n\n**From:** {det['from']}\n**Subject:** {det['subject']}\n\n{det['textBody'][:3000]}", parse_mode="Markdown")

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
