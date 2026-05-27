from aiogram import Router
from aiogram.types import ReactionTypeEmoji
from aiogram.types import Message , CallbackQuery , InputMediaPhoto
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from bot.services.auth import check_user
from bot.services.cards import get_profile_card , get_character_card
from bot.utils.images import image_to_tgFile
from bot.handlers.cards.kb import make_report_keboard , make_profile_keyboard , make_back_kb

from bot.DB.repo.game_ids_repo import GameIDs_repo
from bot.DB.repo.cache_repo import CacheRepo

logger=logging.getLogger(__name__)

rt=Router()

@rt.message(Command("myc"))
async def handle_profile(msg:Message,db_session:AsyncSession):
    tele_id=msg.from_user.id
    user=await check_user(db_session,tele_id)
    uid=await GameIDs_repo(db_session).get_active_UID(tele_id)
    if not user or not uid:
        await msg.reply("please login using /login or /switch ")
        return
    try:
        await msg.react([ReactionTypeEmoji(emoji="👍")])
    except Exception as e:
        logger.error(f"error while reacting to message: {e}")
    res=await get_profile_card(db_session,tele_id)
    if not res:
        kb=make_report_keboard(tele_id,uid.game_id,r_type='PFP')
        await msg.reply("failed to generate profile card , press report to report the issue to the bot admins ",reply_markup=kb)
        return
    if not res.cached:
        photo=await image_to_tgFile(res.card)
    else:
        photo=res.card
    kb=make_profile_keyboard(tele_id,chars=res.data)
    file=await msg.reply_photo(photo=photo,reply_markup=kb)
    file_id = file.photo[0].file_id
    
    await CacheRepo(db_session).set_cache(tele_id,file_id,cache_type='PFP',data=f"{res.data}",slot=None)
    await db_session.commit()
    
@rt.callback_query(lambda c: c.data.startswith("C_card:"))
async def handle_ccard(cb:CallbackQuery,db_session:AsyncSession):
    tele_id=cb.from_user.id
    data=cb.data.split(":")
    to=int(data[1])
    if not tele_id==to:
        await cb.answer("not for you",show_alert=True)
        return
    
    slot=int(data[-1])

    res=await get_character_card(db_session,tele_id,slot)
    if res.cached:
        photo=InputMediaPhoto(media=res.card)
    else:
        file=await image_to_tgFile(res.card)
        photo=InputMediaPhoto(media=file)
    kb=make_back_kb(tele_id)
    file=await cb.message.edit_media(media=photo,reply_markup=kb)
    file_id = file.photo[0].file_id
    
    await CacheRepo(db_session).set_cache(tele_id,file_id,cache_type='CHAR',data=str(slot),slot=slot)
    await db_session.commit()
    
    
@rt.callback_query(lambda c: c.data.startswith("back_P:"))
async def handle_back(cb:CallbackQuery,db_session:AsyncSession):
    tele_id=cb.from_user.id
    data=cb.data.split(":")
    to=int(data[1])
    if not tele_id==to:
        await cb.answer("not for you",show_alert=True)
        return
    uid=await GameIDs_repo(db_session).get_active_UID(tele_id)
    res=await get_profile_card(db_session,tele_id)
    if not res:
        kb=make_report_keboard(tele_id,uid.game_id,r_type='PFP')
        await cb.message.edit_text("failed to generate profile card , press report to report the issue to the bot admins ",reply_markup=kb)
        return
    if not res.cached:
        file=await image_to_tgFile(res.card)
        photo=InputMediaPhoto(media=file)
    else:
        photo=InputMediaPhoto(media=res.card)
    kb=make_profile_keyboard(tele_id,chars=res.data)
    file=await cb.message.edit_media(media=photo,reply_markup=kb)
    file_id = file.photo[0].file_id
    
    await CacheRepo(db_session).set_cache(tele_id,file_id,cache_type='PFP',data=f"{res.data}",slot=None)
    await db_session.commit()