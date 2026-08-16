"""
/myc  : profile card with a button per showcased character.
/allc : every owned character , with a paginated button list.

    C_card:{tele_id}:{slot}       -> profile character card
    back_P:{tele_id}              -> back to the profile card
    GAMEC:{tele_id}:{page}:{index}-> game character card , back button keeps the page
    allc_pg:{tele_id}:{page}      -> another page of buttons , image untouched
    back_A:{tele_id}:{page}       -> back to the /allc card , on the page we left
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from bot.services.cards import (
    get_profile_card,
    get_character_card,
    get_allc_card,
    get_game_char,
    dump_list,
)
from bot.handlers.cards.kb import (
    make_report_keboard,
    make_profile_keyboard,
    make_back_kb,
    make_allc_kb,
    total_pages,
)
from bot.handlers.cards.common import (
    PagedSession,
    active_uid,
    ack,
    notify,
    check_cb,
    render,
    cache_card,
    react,
    reply_sender,
    edit_sender,
    fail_text,
    LIST_EXPIRED,
)

from bot.DB.repo.game_ids_repo import GameIDs_repo

logger = logging.getLogger(__name__)

rt = Router()

PROFILE = "profile"
CHARACTER = "character"
ALLC = "all characters"


def _chars(db_session: AsyncSession, tele_id: int) -> PagedSession:
    """Character list of an /allc message , from redis or rebuilt from the card cache."""
    return PagedSession("allc_session", lambda: _char_list(db_session, tele_id))


async def _char_list(db_session: AsyncSession, tele_id: int):
    res = await get_allc_card(db_session, tele_id)
    return res.data if res else None


@rt.message(Command("myc"))
async def handle_profile(msg: Message, db_session: AsyncSession):
    tele_id = msg.from_user.id
    uid = await active_uid(db_session, tele_id, msg.reply)
    if not uid:
        return
    await react(msg)

    report_kb = make_report_keboard(tele_id, uid.game_id, r_type='PFP')
    res = await get_profile_card(db_session, tele_id)
    if not res:
        await msg.reply(fail_text(PROFILE), reply_markup=report_kb)
        return

    out = await render(
        reply_sender(msg),
        res,
        lambda r: make_profile_keyboard(tele_id, chars=r.data),
        lambda: get_profile_card(db_session, tele_id),
        db_session,
        tele_id,
    )
    if not out:
        await msg.reply(fail_text(PROFILE), reply_markup=report_kb)
        return
    sent, res = out
    await cache_card(db_session, tele_id, sent, 'PFP', data=dump_list(res.data))


@rt.message(Command("allc"))
async def handle_allc(msg: Message, db_session: AsyncSession):
    tele_id = msg.from_user.id
    uid = await active_uid(db_session, tele_id, msg.reply, need_token=True)
    if not uid:
        return
    await react(msg)

    report_kb = make_report_keboard(tele_id, uid.game_id, r_type='ALLC')
    res = await get_allc_card(db_session, tele_id)
    if not res:
        await msg.reply(fail_text(ALLC), reply_markup=report_kb)
        return

    out = await render(
        reply_sender(msg),
        res,
        lambda r: make_allc_kb(tele_id, chars=r.data, page=0),
        lambda: get_allc_card(db_session, tele_id),
        db_session,
        tele_id,
    )
    if not out:
        await msg.reply(fail_text(ALLC), reply_markup=report_kb)
        return
    sent, res = out
    await cache_card(db_session, tele_id, sent, 'ALLC', data=dump_list(res.data))
    await _chars(db_session, tele_id).save(sent, tele_id, res.data)


@rt.callback_query(F.data.startswith("allc_pg:"))
async def handle_allc_page(cb: CallbackQuery, db_session: AsyncSession):
    """Page through the character buttons ; the card image stays untouched."""
    checked = await check_cb(cb, 2)
    if not checked:
        return
    msg, (tele_id, page) = checked

    chars = await _chars(db_session, tele_id).load(msg, tele_id)
    if not chars:
        await notify(cb, LIST_EXPIRED)
        return
    if not 0 <= page < total_pages(chars):
        await notify(cb, "no such page")
        return

    try:
        await msg.edit_reply_markup(
            reply_markup=make_allc_kb(tele_id, chars=chars, page=page)
        )
    except TelegramBadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"could not switch allc page for {tele_id}: {e}")
            await notify(cb, "could not switch page , try again")
            return
    await ack(cb)


@rt.callback_query(F.data.startswith("GAMEC:"))
async def handle_game_char(cb: CallbackQuery, db_session: AsyncSession):
    """Character card built from the live game data , picked from the /allc list."""
    checked = await check_cb(cb, 3)
    if not checked:
        return
    msg, (tele_id, page, index) = checked

    uid = await active_uid(db_session, tele_id, lambda text: notify(cb, text), need_token=True)
    if not uid:
        return

    chars = await _chars(db_session, tele_id).load(msg, tele_id)
    if not chars or index >= len(chars):
        await notify(cb, LIST_EXPIRED)
        return
    char_id = str(chars[index].get("char_id") or "")
    if not char_id:
        await notify(cb, "this character has no id , use /allc again")
        return

    res = await get_game_char(db_session, tele_id, char_id)
    if not res:
        await notify(cb, fail_text(CHARACTER))
        return

    out = await render(
        edit_sender(msg),
        res,
        lambda _: make_back_kb(tele_id, cb="back_A", page=page),
        lambda: get_game_char(db_session, tele_id, char_id),
        db_session,
        tele_id,
    )
    if not out:
        await notify(cb, fail_text(CHARACTER))
        return
    sent, _ = out
    await cache_card(db_session, tele_id, sent, 'GAMEC', data=char_id, char_id=char_id)
    await ack(cb)


@rt.callback_query(F.data.startswith("back_A:"))
async def handle_back_allc(cb: CallbackQuery, db_session: AsyncSession):
    """Back from a game character card to the /allc card , on the page we left."""
    checked = await check_cb(cb, 2)
    if not checked:
        return
    msg, (tele_id, page) = checked

    res = await get_allc_card(db_session, tele_id)
    if not res:
        await notify(cb, fail_text(ALLC))
        return

    out = await render(
        edit_sender(msg),
        res,
        lambda r: make_allc_kb(tele_id, chars=r.data, page=page),
        lambda: get_allc_card(db_session, tele_id),
        db_session,
        tele_id,
    )
    if not out:
        await notify(cb, fail_text(ALLC))
        return
    sent, res = out
    await cache_card(db_session, tele_id, sent, 'ALLC', data=dump_list(res.data))
    await _chars(db_session, tele_id).save(sent, tele_id, res.data)
    await ack(cb)


@rt.callback_query(F.data.startswith("C_card:"))
async def handle_ccard(cb: CallbackQuery, db_session: AsyncSession):
    """Character card built from the public profile , picked from the /myc list."""
    checked = await check_cb(cb, 2)
    if not checked:
        return
    msg, (tele_id, slot) = checked

    res = await get_character_card(db_session, tele_id, slot)
    if not res:
        await notify(cb, fail_text(CHARACTER))
        return

    out = await render(
        edit_sender(msg),
        res,
        lambda _: make_back_kb(tele_id),
        lambda: get_character_card(db_session, tele_id, slot),
        db_session,
        tele_id,
    )
    if not out:
        await notify(cb, fail_text(CHARACTER))
        return
    sent, _ = out
    await cache_card(db_session, tele_id, sent, 'CHAR', data=str(slot), slot=slot)
    await ack(cb)


@rt.callback_query(F.data.startswith("back_P:"))
async def handle_back(cb: CallbackQuery, db_session: AsyncSession):
    """Back from a character card to the /myc profile card."""
    checked = await check_cb(cb, 1)
    if not checked:
        return
    msg, (tele_id,) = checked

    res = await get_profile_card(db_session, tele_id)
    if not res:
        uid = await GameIDs_repo(db_session).get_active_UID(tele_id)
        await msg.edit_caption(
            caption=fail_text(PROFILE),
            reply_markup=make_report_keboard(tele_id, uid.game_id if uid else 0, r_type='PFP'),
        )
        await ack(cb)
        return

    out = await render(
        edit_sender(msg),
        res,
        lambda r: make_profile_keyboard(tele_id, chars=r.data),
        lambda: get_profile_card(db_session, tele_id),
        db_session,
        tele_id,
    )
    if not out:
        await notify(cb, fail_text(PROFILE))
        return
    sent, res = out
    await cache_card(db_session, tele_id, sent, 'PFP', data=dump_list(res.data))
    await ack(cb)
