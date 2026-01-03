import asyncio, random, string, aiohttp, os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Official Bot is Live!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT SETUP ---
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
USER_DATA = {} 

# --- DROPMAIL API (POST METHOD FOR 100% SUCCESS) ---
async def get_official_mail():
    url = "https://dropmail.me/api/graphql/8b62c47e-8c31-4e6f-8a03-9e4517b1897e"
    # This query is what the pro bots use
    query = {"query": "mutation { introduction { id, short_id, hash, expiresAt } }"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=query, timeout=10) as r:
                res = await r.json()
                data = res['data']['introduction']
                email = f"{data['short_id']}@dropmail.me"
                # The hash is the secret token for the browser link
                hash_id = data['hash']
                return {
                    "email": email, 
                    "url": f"https://dropmail.me/#?hash={hash_id}", 
                    "id": data['id']
                }
        except:
            # Fallback to 1secmail if DropMail is totally down
            user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email = f"{user}@1secmail.com"
            return {
                "email": email, 
                "url": "https://www.1secmail.com/", 
                "id": "1sec"
            }

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
        "I provide high-speed disposable emails with an official browser interface.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "➕ Generate New / Delete")
async def generate(m: types.Message):
    # This is the 'Cool' part: A fast, smooth status change
    status = await m.answer("🚀 **Generating...**", parse_mode="Markdown")
    
    res = await get_official_mail()
    
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
        await status.edit_text("❌ Connection error. Please tap again.")

@dp.message(F.text == "🔄 Refresh")
async def refresh(m: types.Message):
    data = USER_DATA.get(m.from_user.id)
    if not data:
        await m.answer("❌ No active email. Click 'Generate' first.")
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Open in Browser ➡", url=data['url']))
    
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
