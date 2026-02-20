import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BASE_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not ADMIN_ID or not BASE_URL:
    raise RuntimeError("ENV o'zgaruvchilar to'liq emas")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 🔑 Bu yerda message_id → user_id saqlaymiz
user_message_map = {}

# /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "BuxDU Yuridik klinika botiga xush kelibsiz!\n"
        "Murojaatingizni yozib qoldiring."
    )

# Foydalanuvchi → ADMINGA
@dp.message()
async def forward_to_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return

    if not message.text:
        await message.answer("Faqat matn yuboring.")
        return

    sent = await bot.send_message(
        ADMIN_ID,
        f"📩 Yangi ariza\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"{message.text}"
    )

    # ADMIN ga yuborilgan xabar ID sini saqlaymiz
    user_message_map[sent.message_id] = message.from_user.id

    await message.answer("Arizangiz qabul qilindi.")

# ADMIN reply → foydalanuvchiga
@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message)
async def reply_to_user(message: types.Message):

    replied_id = message.reply_to_message.message_id

    if replied_id in user_message_map:
        user_id = user_message_map[replied_id]

        await bot.send_message(
            user_id,
            f"📬 Admin javobi:\n\n{message.text}"
        )

        await message.answer("Javob yuborildi ✅")
    else:
        await message.answer("Faqat bot yuborgan xabarga reply qiling.")

# ===== WEBHOOK =====

async def handle_webhook(request: web.Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response()

async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook o'rnatildi")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
