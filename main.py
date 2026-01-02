import asyncio
import random
import string
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- SETUP ---
TOKEN = os.getenv("BOT_TOKEN") # We will add this in Render later
API_URL = "https://api.mail.tm"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def call_api(url, method="GET", data=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{API_URL}{url}", json=data, headers=headers) as r:
            return await r.json()

async def animate(msg, text):
    frames = ["⏳", "🔍", "📩", "✨"]
    for frame in frames:
        try:
            await msg.edit_text(f"{frame} **{text}...**", parse_mode="Markdown")
            await asyncio.sleep(0.4)
        except: pass

@dp.message(Command("start"))
async def start(m: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📧 Generate Email", callback_data="gen"))
    await m.answer(f"✨ **Hello {m.from_user.first_name}!**\nWelcome to the smoothest Temp Mail bot.", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "gen")
async def gen(c: types.CallbackQuery):
    msg = await c.message.edit_text("🚀 **Connecting...**")
    doms = await call_api("/domains")
    domain = doms['hydra:member'][0]['domain']
    addr, pwd = f"{''.join(random.choices(string.ascii_lowercase, k=8))}@{domain}", "pass12345"
    
    await animate(msg, "Creating Secure Inbox")
    await call_api("/accounts", "POST", {"address": addr, "password": pwd})
    tk_res = await call_api("/token", "POST", {"address": addr, "password": pwd})
    token = tk_res['token']

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔄 Check Inbox", callback_data=f"ref_{token}"))
    await msg.edit_text(f"✅ **Ready!**\n\n📧 `{addr}`\n\n_Tap email to copy. Click below to check mail._", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("ref_"))
async def ref(c: types.CallbackQuery):
    token = c.data.split("_")[1]
    await c.answer("Checking...")
    mails = await call_api("/messages", token=token)
    if not mails['hydra:member']:
        await c.answer("No emails yet! 📬", show_alert=True)
    else:
        m = mails['hydra:member'][0]
        await c.message.answer(f"📩 **New Mail!**\n\n👤 From: {m['from']['address']}\n📝 Subject: {m['subject']}\n\n{m['intro']}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
