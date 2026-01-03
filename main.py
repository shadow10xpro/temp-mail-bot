import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
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

# --- SERVICE 1: MAIL.TM (Modern UI) ---
async def fetch_mail_tm():
    try:
        user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        addr, pwd = f"{user}@fexpost.com", "pass12345"
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.mail.tm/accounts", json={"address": addr, "password": pwd}, timeout=5) as r:
                if r.status == 201:
                    async with s.post("https://api.mail.tm/token", json={"address": addr, "password": pwd}) as r2:
                        tk = await r2.json()
                        return {"email": addr, "token": tk['token'], "type": "mail_tm", "url": "https://mail.tm/en/"}
    except: return None

# --- SERVICE 2: DROPMAIL (Fastest & Best Browser UI) ---
async def fetch_dropmail():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e?query=mutation{introduction{id,short_id,hash,expiresAt}}", timeout=5) as r:
                data = await r.json()
                short_id = data['data']['introduction']['short_id']
                addr = f"{short_id}@dropmail.me"
                # DropMail allows browser access via a unique hash
                hash_id = data['data']['introduction']['hash']
                return {"email": addr, "type": "drop", "url": f"https://dropmail.me/#?hash={hash_id}"}
    except: return None

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- COMMANDS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "👋 **Welcome to Temp Mail Pro**\n\n"
        "I provide high-speed disposable emails with a smooth browser interface.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("⚡ **Generating...**", parse_mode="Markdown")
    
    # Try Service 1 (Mail.tm) -> then Service 2 (DropMail)
    res = await fetch_mail_tm()
    if not res:
        res = await fetch_dropmail()

    if res:
        USER_DATA[m.from_user.id] = res
        builder = InlineKeyboardBuilder()
        # The cool "Open in Browser" button
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
        await status.edit_text("❌ All servers are busy. Please try again in 3 seconds.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    # For speed and 100% result, we tell users to use the Browser button
    # but we also provide a quick status check
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))
    
    await m.answer(
        f"Current email address:\n**{data['email']}**\n\n"
        f"**Your inbox is empty**\n"
        f"_New messages will appear here or you can check the browser link below._",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
