import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
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

async def call_api(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as r:
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
    await m.answer("✨ **Welcome to Temp Mail Pro**\n\nUse the buttons below. Your OTP will appear right here in the chat!", reply_markup=main_menu(), parse_mode="Markdown")

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    domains = ["1secmail.com", "1secmail.org", "kzbat.com", "vjuum.com"]
    domain = random.choice(domains)
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{domain}"
    
    USER_DATA[m.from_user.id] = {"email": email, "user": user, "domain": domain}
    
    # Adding the "Open Browser" button back
    builder = InlineKeyboardBuilder()
    # We use the official 1secmail link
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=f"https://www.1secmail.com/mailbox/?login={user}&domain={domain}"))
    
    await m.answer(
        f"✅ **Your temporary email is ready!**\n\n"
        f"📧 `{email}`\n\n"
        f"**Tap the email to copy it.**\n"
        f"Click **Refresh** to see your OTP here, or use the button below to open the web view.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_DATA:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    data = USER_DATA[user_id]
    check_url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
    messages = await call_api(check_url)
    
    if not messages:
        await m.answer(f"📧 **Inbox:** `{data['email']}`\n\n**Status:** No messages yet... 📬", parse_mode="Markdown")
    else:
        msg_id = messages[0]['id']
        read_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={msg_id}"
        msg_content = await call_api(read_url)
        
        if msg_content:
            await m.answer(
                f"📩 **NEW EMAIL RECEIVED!**\n\n"
                f"👤 **From:** `{msg_content.get('from')}`\n"
                f"📝 **Subject:** {msg_content.get('subject')}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"{msg_content.get('textBody', 'No content')[:3000]}\n\n"
                f"━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
