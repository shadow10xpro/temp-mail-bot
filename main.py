import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- HEARTBEAT FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Ultra-Fast Bot is Live"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} # Stores user session info

# Professional Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Content-Type": "application/json"
}

# --- API CORE (DROPMAIL) ---
async def call_api(query):
    url = "https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e"
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for _ in range(3): # Auto-retry 3 times for speed
            try:
                async with session.post(url, json={"query": query}, timeout=10) as r:
                    if r.status == 200:
                        return await r.json()
            except:
                await asyncio.sleep(0.5)
    return None

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Generate New / Delete")
    kb.button(text="🔄 Refresh")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

# --- BOT HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer(
        "✨ **Welcome to Temp Mail Official**\n\n"
        "OTPs and Messages will arrive directly in this chat. Use the menu below to start.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def cmd_gen(m: types.Message):
    status = await m.answer("🚀 **Generating official email...**")
    
    query = "mutation { introduction { id, short_id, hash } }"
    res = await call_api(query)
    
    if res and 'data' in res:
        data = res['data']['introduction']
        email = f"{data['short_id']}@dropmail.me"
        # The Hash Link for the official browser look
        link = f"https://dropmail.me/#?hash={data['hash']}"
        
        USER_DATA[m.from_user.id] = {"id": data['id'], "email": email, "url": link}
        
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=link))
        
        await status.delete()
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"📧 `{email}`",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await status.edit_text("❌ Server busy. Please try again in a few seconds.")

@dp.message(F.text == "🔄 Refresh")
async def cmd_refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    # GraphQL query to get the mail content directly
    query = f"query {{ session(id: \"{data['id']}\") {{ mails {{ fromAddr, subject, text, decode_status }} }} }}"
    res = await call_api(query)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))

    if res and res.get('data') and res['data']['session']['mails']:
        mail = res['data']['session']['mails'][-1] # Show the latest mail
        
        # Format the received message nicely
        mail_text = (
            f"📩 **NEW MESSAGE RECEIVED!**\n\n"
            f"👤 **From:** `{mail['fromAddr']}`\n"
            f"📝 **Subject:** {mail['subject']}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"{mail['text'][:3000]}\n\n"
            f"━━━━━━━━━━━━━━━"
        )
        await m.answer(mail_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await m.answer(
            f"Current email address:\n`{data['email']}`\n\n"
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
