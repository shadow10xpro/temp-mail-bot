import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
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

# --- COMMANDS ---
@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        "✨ **Welcome to Temp Mail Pro**\n\n"
        "I provide instant disposable emails. Everything works right here in this chat!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # Instant generation using 1secmail
    domains = ["1secmail.com", "1secmail.org", "1secmail.net", "kzbat.com", "vjuum.com"]
    domain = random.choice(domains)
    user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{user}@{domain}"
    
    # Save user data locally
    USER_DATA[m.from_user.id] = {"email": email, "user": user, "domain": domain}
    
    await m.answer(
        f"✅ **Your temporary email is ready!**\n\n"
        f"📧 `{email}`\n\n"
        f"**Tap the email address to copy it.**\n"
        f"When you expect a mail, click the **Refresh** button below.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    user_id = m.from_user.id
    if user_id not in USER_DATA:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    data = USER_DATA[user_id]
    # Check for messages
    check_url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={data['user']}&domain={data['domain']}"
    messages = await call_api(check_url)
    
    if not messages:
        await m.answer(
            f"📧 **Inbox:** `{data['email']}`\n\n"
            f"**Status:** No messages yet... 📬",
            parse_mode="Markdown"
        )
    else:
        # Get the most recent message ID
        msg_id = messages[0]['id']
        # Fetch message content
        read_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={data['user']}&domain={data['domain']}&id={msg_id}"
        msg_content = await call_api(read_url)
        
        if msg_content:
            # Prepare clean message text
            from_addr = msg_content.get('from', 'Unknown')
            subject = msg_content.get('subject', 'No Subject')
            body = msg_content.get('textBody', 'No text content available.')
            
            await m.answer(
                f"📩 **NEW EMAIL RECEIVED!**\n\n"
                f"👤 **From:** `{from_addr}`\n"
                f"📝 **Subject:** {subject}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"{body[:3500]}\n\n"
                f"━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
        else:
            await m.answer("❌ Error reading the message. Try again.")

async def main():
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
