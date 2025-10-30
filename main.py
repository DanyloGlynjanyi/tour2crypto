# main.py
import asyncio
import logging
import os

from aiogram import Dispatcher

from bot.core import bot
from bot.db.engine import db
from bot.services import user_router, admin_router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("runner")

SKIP_UPDATES = os.getenv("SKIP_UPDATES", "1") == "1"

async def main():
    log.info("Connecting DB...")
    await db.connect()

    dp = Dispatcher()
    dp.include_router(user_router)
    dp.include_router(admin_router)

    try:
        await dp.start_polling(bot, allowed_updates=None if SKIP_UPDATES else ...)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
