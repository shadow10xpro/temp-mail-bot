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

# --- DROPMAIL GRAPHQL API (The Most Professional Choice) ---
async def call_dropmail(query):
    url = "https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"query": query}, timeout=10) as r:
                return await r.json()
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
        "👋 **Welcome to Temp Mail Official**\n\n"
        "I provide high-speed disposable emails with a working browser interface. OTPs arrive instantly here!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    status = await m.answer("🚀 **Generating official inbox...**")
    
    # 1. Create a new session via GraphQL (Instant)
    query = "mutation { introduction { id, short_id, hash } }"
    res = await call_dropmail(query)
    
    if res and 'data' in res:
        data = res['data']['introduction']
        email = f"{data['short_id']}@dropmail.me" # Base domain, will use others if available
        # The Secret Hash logs you in automatically via the URL
        browser_url = f"https://dropmail.me/#?hash={data['hash']}"
        
        USER_DATA[m.from_user.id] = {"email": email, "id": data['id'], "url": browser_url}
        
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=browser_url))
        
        await status.delete()
        await m.answer(
            f"Your old email address has been successfully deleted\n\n"
            f"New temporary email address generated:\n\n"
            f"📧 **{email}**",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await status.edit_text("❌ Server busy. Please try again.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    # Check for messages via GraphQL
    query = f"query {{ session(id: \"{data['id']}\") {{ mails {{ fromAddr, toAddr, subject, text }} }} }}"
    res = await call_dropmail(query)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))

    if res and res.get('data') and res['data']['session']['mails']:
        mail = res['data']['session']['mails'][-1] # Get the latest mail
        await m.answer(
            f"📩 **New Message Found!**\n\n"
            f"👤 **From:** `{mail['fromAddr']}`\n"
            f"📝 **Subject:** {mail['subject']}\n\n"
            f"{mail['text'][:3000]}",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    else:
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
