import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Pro Bot Live"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

# Realistic headers to bypass "Server Busy"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json"
}

# --- SERVICE 1: DROPMAIL (Highest OTP Success) ---
async def get_dropmail():
    url = "https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e"
    query = {"query": "mutation { introduction { id, short_id, hash } }"}
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        try:
            async with s.post(url, json=query, timeout=8) as r:
                res = await r.json()
                d = res['data']['introduction']
                # Token link for auto-login
                link = f"https://dropmail.me/#?hash={d['hash']}"
                return {"email": f"{d['short_id']}@dropmail.me", "id": d['id'], "url": link, "type": "drop"}
        except: return None

# --- SERVICE 2: SECMAIL (Instant Backup) ---
async def get_secmail():
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = random.choice(["1secmail.com", "1secmail.org", "kzbat.com"])
    email = f"{user}@{domain}"
    link = f"https://www.1secmail.com/mailbox/?login={user}&domain={domain}"
    return {"email": email, "user": user, "domain": domain, "url": link, "type": "sec"}

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- BOT LOGIC ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("👋 **Welcome to Temp Mail Official**\n\nOTPs arrive here instantly. Use the menu below.", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("🚀 **Searching for clean domain...**")
    
    # Try Service 1 (Best for OTP)
    res = await get_dropmail()
    
    # If Service 1 is busy, try Service 2 immediately
    if not res:
        await status.edit_text("⚡ **Switching to Backup Server...**")
        res = await get_secmail()

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
        await status.edit_text("❌ All mail servers are under maintenance. Try in 1 minute.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    # Check for messages based on service type
    async with aiohttp.ClientSession(headers=HEADERS) as s:
        if data['type'] == "drop":
            query = {"query": f"query {{ session(id: \"{data['id']}\") {{ mails {{ fromAddr, subject, text }} }} }}"}
            async with s.post("https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e", json=query) as r:
                res = await r.json()
                mails = res['data']['session']['mails']
        else:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
            async with s.get(url) as r:
                items = await r.json()
                mails = []
                if items:
                    url2 = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={items[0]['id']}"
                    async with s.get(url2) as r2:
                        m = await r2.json()
                        mails.append({"fromAddr": m['from'], "subject": m['subject'], "text": m['textBody']})

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))

    if not mails:
        await m.answer(f"Current email address:\n**{data['email']}**\n\n**Your inbox is empty**", reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        mail = mails[-1]
        await m.answer(f"📩 **New Message!**\n\n👤 **From:** `{mail['fromAddr']}`\n📝 **Subject:** {mail['subject']}\n\n{mail['text'][:3000]}", reply_markup=builder.as_markup(), parse_mode="Markdown")

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
