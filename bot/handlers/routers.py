from aiogram import Dispatcher , Router
from aiogram.filters import Command
import logging

from bot.handlers.start import rt as start
from bot.handlers.auth.auth import rt as login
from bot.handlers.cards.common import rt as cards_ui
from bot.handlers.cards.profile import rt as profile
from bot.handlers.endgames import rt as endgames
from bot.handlers.groups import rt as groups
from bot.handlers.live_cards import rt as live_cards
from bot.admin.admin_commands import rt as admins
from bot.handlers.settings import rt as settings
from bot.handlers.blueprints.blueprints import rt as bp
from bot.handlers.guides.guides import rt as guides

#### WARNING - KEEP " groups " ROUTER LAST IN THE LIST TO AVOID CONFLICTS
routers=[
    start,
    login,
    cards_ui,
    profile,
    endgames,
    live_cards,
    admins,
    settings,
    bp,
    guides,
    groups,
    ]
logger=logging.getLogger(__name__)

main_rt=Router()

def setup_routers(dp:Dispatcher)->set[str]|None:
    try:
        for rt in routers:
            main_rt.include_router(rt)
        dp.include_router(main_rt)
        return get_commands(main_rt)
    except Exception as e:
        logger.error("error setting up routers")
        
def get_commands(router:Router)->set[str]:
    commands=set()
    for handler in router.message.handlers:
        for filter in handler.filters:
            callback=filter.callback
            if isinstance(callback,Command):
                for cmd in callback.commands:
                    commands.add(cmd.lower())
    for s_rt in router.sub_routers:
        commands.update(get_commands(s_rt))
    return commands