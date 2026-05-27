from endfield_cards import EFCard
from endfield import Endfield
from pydantic import BaseModel , ConfigDict
from PIL import Image
from datetime import datetime , timezone
import logging
import asyncio

from bot.DB.repo.game_ids_repo import GameIDs_repo
from bot.DB.repo.user_setting_repo import UserSettingsRepo
from bot.utils.images import image_to_tgFile
from bot.utils.auth import decrypt_token

logger=logging.getLogger(__name__)

class LiveStatsRes(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    card:Image.Image | None
    time:datetime | None
    seconds: int | None = None
    success:bool
    msg: str
    
async def get_live_stats_card(db_session,tele_id:int)->LiveStatsRes:
    ## Don't use caching , it uses internal cache
    game_id=await GameIDs_repo(db_session).get_active_UID(tele_id)
    if not game_id:
        return LiveStatsRes(
            card=None,
            time=None,
            success=False,
            msg="No active game ID found. Please login using /login or /switch."
        )
    token=game_id.auth_token
    if not token:
        return LiveStatsRes(
            card=None,
            time=None,
            success=False,
            msg="Please login with /token_login to access live stats."
        )
    try:
        async with EFCard() as ef_card:
            token=decrypt_token(token)
            card=await ef_card.get_live_stats_card(game_id.game_id,token=token)
            if card:
                return LiveStatsRes(
                    card=card.img,
                    time=card.full_recovery_time,
                    seconds=card.full_recovery_seconds,
                    success=True,
                    msg=f"full recovery time: {card.full_recovery_minutes//60}h\
                    {(card.full_recovery_minutes%60)}m" if card.full_recovery_time >\
                    datetime.now(tz=timezone.utc) else "fully recovered"
                )
            else:
                return LiveStatsRes(
                    card=None,
                    time=None,
                    success=False,
                    msg="Failed to retrieve live stats card. Please try again later."
                )
    except Exception as e:
        logger.error(f"Error fetching live stats card: {str(e)}")
        return LiveStatsRes(
            card=None,
            time=None,
            success=False,
            msg=f"An error occurred while fetching live stats"
        )

async def get_live_factory_card(db_session,tele_id:int)->LiveStatsRes:
    ### Dont use caching , it uses internal cache
    game_id=await GameIDs_repo(db_session).get_active_UID(tele_id)
    if not game_id:
        return LiveStatsRes(
            card=None,
            time=None,
            success=False,
            msg="No active game ID found. Please login using /login or /switch."
        )
    token=game_id.auth_token
    if not token:
        return LiveStatsRes(
            card=None,
            time=None,
            success=False,
            msg="Please login with /token_login to access live stats."
        )
    try:
        async with EFCard() as ef_card:
            token=decrypt_token(token)
            card=await ef_card.get_factory_stats_card(game_id.game_id,token=token)
            if card:
                return LiveStatsRes(
                    card=card,
                    time=None,
                    success=True,
                    msg="Factory stats card retrieved successfully."
                )
            else:
                return LiveStatsRes(
                    card=None,
                    time=None,
                    success=False,
                    msg="Failed to retrieve factory stats card. Please try again later."
                )
    except Exception as e:
        logger.error(f"Error fetching factory stats card: {str(e)}")
        return LiveStatsRes(
            card=None,
            time=None,
            success=False,
            msg=f"An error occurred while fetching factory stats"
        )


async def send_recovery_notification(tele_id:int, retries:int=3):
    from bot.core.main import bot
    from bot.DB.asyncsessions import session_factory
    
    async with session_factory() as db_session:
        for attempt in range(retries):
            try:
                live_stats = await get_live_stats_card(db_session, tele_id)
                if not live_stats.success:
                    await asyncio.sleep(10)
                    continue
                now = datetime.now(tz=timezone.utc)
                if live_stats.time is None or live_stats.time <= now:
                    text = "Your Sanity points have fully recovered!\nYou can check your live stats with /notes"
                    if live_stats.card:
                        card_file = await image_to_tgFile(live_stats.card)
                        await bot.send_photo(tele_id, card_file, caption=text)
                    else:
                        await bot.send_message(tele_id, text)
                    logger.info(f"Sent recovery notification to user {tele_id}")
                    break
                else:
                    remaining_seconds = (live_stats.time - now).total_seconds()
                    sleep_time = min(remaining_seconds, 300)
                    await asyncio.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Error sending recovery notification to user {tele_id} on attempt {attempt+1}: {str(e)}")
                await asyncio.sleep(10)
                if attempt == retries - 1:
                    logger.error(f"Failed to send recovery notification to user {tele_id} after {retries} attempts.")
                    
# daily reminder of daily tasks IST 10:00 PM 

async def send_daily_reminder():
    from bot.core.main import bot
    from bot.DB.asyncsessions import session_factory
    
    async with session_factory() as db_session:
        users=await UserSettingsRepo(db_session).get_all_users_with_daily_reminder()
        for tele_id in users:
            try:
                token=await GameIDs_repo(db_session).get_active_UID(tele_id)
                if not token or not token.auth_token:
                    await bot.send_message(tele_id, "Make sure to complete your daily tasks or you can login with /token_login to get detailed reminder in future")
                    await asyncio.sleep(10)
                    continue
                else:
                    token=decrypt_token(token.auth_token)
                    async with Endfield() as endfield:
                        stats=await endfield.get_game_stats(token)
                        if stats:
                            if stats.daily_points.current < stats.daily_points.max:
                                text=f"Reminder: You have {stats.daily_points.current}/{stats.daily_points.max} daily points.\n"
                                text+=f"\nYour current sanity is {stats.sanity_point.current}/{stats.sanity_point.max}.\n"
                                text+="Don't forget to complete your daily tasks!"
                                await bot.send_message(tele_id, text)
                await asyncio.sleep(10)  # Sleep to avoid hitting game API rate limits
            except Exception as e:
                logger.error(f"Error sending daily reminder to user {tele_id}: {str(e)}")
                await asyncio.sleep(10)
                
async def send_weekly_reminder():
    from bot.core.main import bot
    from bot.DB.asyncsessions import session_factory
    async with session_factory() as db_session:
        users=await UserSettingsRepo(db_session).get_all_users_with_weekly_reminder()
        for tele_id in users:
            try:
                token=await GameIDs_repo(db_session).get_active_UID(tele_id)
                if not token or not token.auth_token:
                    await bot.send_message(tele_id, "Make sure to complete your weekly tasks or you can login with /token_login to get detailed reminder in future")
                    await asyncio.sleep(10)
                    continue
                else:
                    token=decrypt_token(token.auth_token)
                    async with Endfield() as endfield:
                        stats=await endfield.get_game_stats(token)
                        if stats:
                            if stats.weekly_points.score < stats.weekly_points.total:
                                text=f"Reminder: You have {stats.weekly_points.score}/{stats.weekly_points.total} weekly points.\n"
                                text+=f"\nYour current sanity is {stats.sanity_point.current}/{stats.sanity_point.max}.\n"
                                text+="Don't forget to complete your weekly tasks!"
                                await bot.send_message(tele_id, text)
                await asyncio.sleep(10)  # Sleep to avoid hitting game API rate limits
            except Exception as e:
                logger.error(f"Error sending weekly reminder to user {tele_id}: {str(e)}")
                await asyncio.sleep(10)
                
async def perform_daily_tasks():
    from bot.core.main import bot
    from bot.DB.asyncsessions import session_factory
    async with session_factory() as db_session:
        users=await UserSettingsRepo(db_session).get_all_users_with_perform_daily()
        for tele_id in users:
            try:
                token=await GameIDs_repo(db_session).get_active_UID(tele_id)
                if not token or not token.auth_token:
                    await bot.send_message(tele_id, "Please login with /token_login to allow auto performing daily tasks")
                    await asyncio.sleep(10)
                    continue
                else:
                    token=decrypt_token(token.auth_token)
                    async with Endfield() as endfield:
                        result=await endfield.perform_daily_sign(token)
                        text=f"Daily tasks performed: {result}"
                        await bot.send_message(tele_id, text)
                await asyncio.sleep(10)  # Sleep to avoid hitting game API rate limits
            except Exception as e:
                logger.error(f"Error performing daily tasks for user {tele_id}: {str(e)}")
                await asyncio.sleep(10)
    