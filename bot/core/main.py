from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties


from bot.handlers.routers import setup_routers
from bot.middleware.dbm import DBMiddleware
from bot.middleware.ratelimit import RateLimitMiddleware
from bot.config.config import BOT_TOKEN
from bot.core.startup import on_startup
from bot.core.shutdown import on_shutdown

dp=Dispatcher()
dp.message.middleware(RateLimitMiddleware())
dp.message.middleware(DBMiddleware())
dp.callback_query.middleware(DBMiddleware())
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)

setup_routers(dp)

bot=Bot(token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)