import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "TempMail Pro 2026 - Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

# Professional Header Spoofing
def get_headers():
    return {
        "User-Agent": random.choice([
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UD1A.230805.019) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]),
        "Accept": "application/json"
    }

# --- PROVIDER 1: DROPMAIL (Official Token Link) ---
async def try_dropmail():
    url = "https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e"
    query = {"query": "mutation { introduction { id, short_id, hash } }"}
    async with aiohttp.ClientSession(headers=get_headers()) as s:
        try:
            async with s.post(url, json=query, timeout=8) as r:
                if r.status == 200:
                    data = (await r.json())['data']['introduction']
                    return {
                        "email": f"{data['short_id']}@dropmail.me",
                        "id": data['id'],
                        "url": f"https://dropmail.me/#?hash={data['hash']}",
                        "type": "dropmail"
                    }
        except: return None

# --- PROVIDER 2: MAIL.TM (backup with account) ---
async def try_mail_tm():
    try:
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email, pwd = f"{user}@fexpost.com", "pass123456"
        async with aiohttp.ClientSession(headers=get_headers()) as s:
            async with s.post("https://api.mail.tm/accounts", json={"address": email, "password": pwd}, timeout=8) as r1:
                if r1.status == 201:
                    async with s.post("https://api.mail.tm/token", json={"address": email, "password": pwd}) as r2:
                        res = await r2.json()
                        return {
                            "email": email,
                            "token": res['token'],
                            "url": "https://mail.tm/en/",
                            "type": "mail_tm"
                        }
    except: return None

# --- PROVIDER 3: 1SECMAIL (No-Registration Instant) ---
async def try_1secmail():
    try:
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        domain = random.choice(["1secmail.com", "1secmail.org", "kzbat.com"])
        return {
            "email": f"{user}@{domain}",
            "user": user,
            "domain": domain,
            "url": f"https://www.1secmail.com/mailbox/?login={user}&domain={domain}",
            "type": "1sec"
        }
    except: return None

# --- UI MENU ---
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- BOT LOGIC ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🚀 **TempMail Pro Official v2026**\n\nI use a triple-server system to ensure 100% availability. Generate an email now!", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("🚀 **Searching for an active server...**")
    
    # Failover Logic: Try DropMail -> Mail.tm -> 1secmail
    res = await try_dropmail()
    if not res:
        await status.edit_text("⚡ **Server 1 Busy... Switching to Server 2...**")
        res = await try_mail_tm()
    if not res:
        await status.edit_text("⚡ **Server 2 Busy... Switching to Server 3...**")
        res = await try_1secmail()

    if res:
        USER_DATA[m.from_user.id] = res
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=res['url']))
        
        await status.delete()
        await m.answer(
            f"✅ **Temp Email Ready!**\n\n"
            f"📧 `{res['email']}`\n\n"
            f"Tap to copy. OTPs will appear directly in this chat or via the browser link below.",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await status.edit_text("❌ All global servers are under heavy load. Please try again in 10 seconds.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ Please generate an email first.")
        return

    # Direct Message Fetching
    async with aiohttp.ClientSession(headers=get_headers()) as s:
        mails = []
        try:
            if data['type'] == "dropmail":
                query = {"query": f"query {{ session(id: \"{data['id']}\") {{ mails {{ fromAddr, subject, text }} }} }}"}
                async with s.post("https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e", json=query) as r:
                    res = await r.json()
                    mails = res['data']['session']['mails']
            elif data['type'] == "1sec":
                url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
                async with s.get(url) as r:
                    items = await r.json()
                    if items:
                        url2 = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={items[0]['id']}"
                        async with s.get(url2) as r2:
                            m2 = await r2.json()
                            mails.append({"fromAddr": m2['from'], "subject": m2['subject'], "text": m2['textBody']})
        except: pass

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))

    if not mails:
        await m.answer(f"📧 `{data['email']}`\n\n**Inbox is empty**\n_Waiting for incoming codes..._", reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        mail = mails[-1]
        await m.answer(f"📩 **New Message!**\n\n👤 **From:** `{mail['fromAddr']}`\n📝 **Subject:** {mail['subject']}\n\n{mail['text'][:3000]}", reply_markup=builder.as_markup(), parse_mode="Markdown")

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
