from asyncio import run
import logging

from bot.core.main import bot, dp
from bot.DB.engine import engine

logger = logging.getLogger(__name__)

async def start_polling():
    try:
        logger.info("Starting bot in polling mode...")
        await dp.start_polling(bot)
    finally:
        await engine.dispose()
        await bot.session.close()
        logger.info("Bot polling stopped")
        
if __name__=="__main__":
    try:
        run(start_polling())
    except Exception as e:
        logger.error(f"error while starting : {e}")