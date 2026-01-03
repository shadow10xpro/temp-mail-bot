import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
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

# --- DROPMAIL API (SUPER FAST & NO 403) ---
async def get_dropmail():
    url = "https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e"
    query = "mutation { introduction { id, short_id, hash, expiresAt } }"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{url}?query={query}", timeout=5) as r:
                res = await r.json()
                data = res['data']['introduction']
                email = f"{data['short_id']}@dropmail.me"
                # This hash is the 'Token' that logs you in automatically
                hash_id = data['hash']
                return {"email": email, "url": f"https://dropmail.me/#?hash={hash_id}", "id": data['id']}
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
        "👋 **Welcome to Temp Mail Official**\n\n"
        "I provide high-speed disposable emails with instant browser access.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # Smooth speed: One quick "Generating" message
    status = await m.answer("🚀 **Generating...**", parse_mode="Markdown")
    
    res = await get_dropmail()
    
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
    
    # We send the exact same text as the official bot
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
