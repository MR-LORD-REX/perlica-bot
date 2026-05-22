from bot.DB.engine import engine
from bot.DB.base import base as Base
from bot.DB import Users,Cache,GameID

from endfield import Endfield

import logging
import sys

base=Base()
logger=logging.getLogger(__name__)

async def init_db():
    try:
        async with engine.begin() as con:
            await con.run_sync(base.metadata.create_all)
            logger.info("databases created succesfully")
        # async with Endfield() as ef:
        #     await ef.update_assets()
        #     logger.info("endfield assets updated successfully")
    except Exception as e:
        logger.error(f"error in startup : {e}")
        sys.exit()
        
async def on_startup():
    await init_db()