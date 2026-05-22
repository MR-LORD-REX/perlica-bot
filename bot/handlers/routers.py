from aiogram import Dispatcher
import logging

from bot.handlers.start import rt as start
from bot.handlers.auth.auth import rt as login
from bot.handlers.cards.profile import rt as profile

routers=[start,login,profile]
logger=logging.getLogger(__name__)

def setup_routers(dp:Dispatcher):
    try:
        for rt in routers:
            dp.include_router(rt)
    except Exception as e:
        logger.error("error setting up routers")