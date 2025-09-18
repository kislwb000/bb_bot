import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from database.db import init_db
from handlers import add_admin, common, event, score, score_manage, start, team
from handlers.view import routers as view_routers
from logger import app_logger

app_logger.info("Бот запускается...")
logger = app_logger

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN") or ""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(add_admin.router)
dp.include_router(event.router)
dp.include_router(score.router)
dp.include_router(team.router)
dp.include_router(common.router)
dp.include_router(score_manage.router)
for router in view_routers:
    dp.include_router(router)


async def main():
    await init_db()
    print("Бот запущен ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("⛔ Бот остановлен вручную.")
