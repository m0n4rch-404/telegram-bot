import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# ====== LOG ======
logging.basicConfig(level=logging.INFO)

# ====== ENV ======
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
BASE_URL = os.getenv("WEBHOOK_URL")  # masalan: https://your-app.onrender.com

if not TOKEN or not ADMIN_ID or not BASE_URL:
    raise RuntimeError("ENV o'zgaruvchilar to'liq emas (BOT_TOKEN, ADMIN_ID, WEBHOOK_URL).")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

# ====== INIT ======
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ====== HANDLERS ======

# /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "BuxDU Yuridik klinika botiga xush kelibsiz!\n"
        "Murojaatingizni to'liq matn ko'rinishida yozib qoldiring.\n"
        "Murojaatlar 3 kun ichida ko'rib chiqiladi va javob yuboriladi."
    )

# Foydalanuvchi xabari → ADMINGA
@dp.message()
async def forward_to_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return

    if not message.text:
        await message.answer("Iltimos, matn ko'rinishida ariza yuboring.")
        return

    text = (
        f"📩 Yangi ariza\n\n"
        f"👤 Ism: {message.from_user.full_name}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"{message.text}"
    )

    await bot.send_message(ADMIN_ID, text)
    await message.answer("Sizning arizangiz qabul qilindi. Tez orada javob beriladi.")

# Admin javobini foydalanuvchiga yuborish (format: user_id: javob matni)
@dp.message(lambda m: m.from_user.id == ADMIN_ID)
async def reply_to_user(message: types.Message):
    if ":" not in message.text:
        await message.answer("Iltimos, javobni shunday formatda yuboring: user_id: javob matni")
        return

    try:
        user_id_str, reply_text = message.text.split(":", 1)
        user_id = int(user_id_str.strip())
        await bot.send_message(user_id, f"📬 Admin javobi:\n\n{reply_text.strip()}")
        await message.answer("Javob foydalanuvchiga yuborildi ✅")
    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

# ====== WEBHOOK ======
async def handle_webhook(request: web.Request):
    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.error(f"Webhook xato: {e}")
    return web.Response()

async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    logging.info("Webhook o'chirildi")

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# ====== RUN ======
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

