
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from bot.services.cards import dump_list
from bot.services.endgames import get_monument_card, get_monument_domain_card
from bot.handlers.cards.kb import (
    make_report_keboard,
    make_monument_kb,
    make_back_kb,
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

logger = logging.getLogger(__name__)

rt = Router()

MONUMENT = "monument"
DOMAIN = "monument domain"


def _domains(db_session: AsyncSession, tele_id: int) -> PagedSession:
    """Domain list of a monument message , from redis or rebuilt from the card cache."""
    return PagedSession("monu_session", lambda: _domain_list(db_session, tele_id))


async def _domain_list(db_session: AsyncSession, tele_id: int):
    res = await get_monument_card(db_session, tele_id)
    return res.data if res else None


@rt.message(Command("monument"))
async def handle_monument(msg: Message, db_session: AsyncSession):
    tele_id = msg.from_user.id
    uid = await active_uid(db_session, tele_id, msg.reply, need_token=True)
    if not uid:
        return
    await react(msg)

    report_kb = make_report_keboard(tele_id, uid.game_id, r_type='MONUA')
    res = await get_monument_card(db_session, tele_id)
    if not res:
        await msg.reply(fail_text(MONUMENT), reply_markup=report_kb)
        return

    out = await render(
        reply_sender(msg),
        res,
        lambda r: make_monument_kb(tele_id, domains=r.data, page=0),
        lambda: get_monument_card(db_session, tele_id),
        db_session,
        tele_id,
    )
    if not out:
        await msg.reply(fail_text(MONUMENT), reply_markup=report_kb)
        return
    sent, res = out
    await cache_card(db_session, tele_id, sent, 'MONUA', data=dump_list(res.data))
    await _domains(db_session, tele_id).save(sent, tele_id, res.data)


@rt.callback_query(F.data.startswith("monu_pg:"))
async def handle_monument_page(cb: CallbackQuery, db_session: AsyncSession):
    """Page through the domain buttons ; the card image stays untouched."""
    checked = await check_cb(cb, 2)
    if not checked:
        return
    msg, (tele_id, page) = checked

    domains = await _domains(db_session, tele_id).load(msg, tele_id)
    if not domains:
        await notify(cb, LIST_EXPIRED)
        return
    if not 0 <= page < total_pages(domains):
        await notify(cb, "no such page")
        return

    try:
        await msg.edit_reply_markup(
            reply_markup=make_monument_kb(tele_id, domains=domains, page=page)
        )
    except TelegramBadRequest as e:
        if "not modified" not in str(e).lower():
            logger.error(f"could not switch monument page for {tele_id}: {e}")
            await notify(cb, "could not switch page , try again")
            return
    await ack(cb)


@rt.callback_query(F.data.startswith("MONUD:"))
async def handle_domain(cb: CallbackQuery, db_session: AsyncSession):
    """Card of a single monument domain."""
    checked = await check_cb(cb, 3)
    if not checked:
        return
    msg, (tele_id, page, slot) = checked

    uid = await active_uid(db_session, tele_id, lambda text: notify(cb, text), need_token=True)
    if not uid:
        return

    domains = await _domains(db_session, tele_id).load(msg, tele_id)
    if not domains or slot not in [d.get("slot") for d in domains]:
        await notify(cb, LIST_EXPIRED)
        return

    res = await get_monument_domain_card(db_session, tele_id, slot)
    if not res:
        await notify(cb, fail_text(DOMAIN))
        return

    out = await render(
        edit_sender(msg),
        res,
        lambda _: make_back_kb(tele_id, cb="back_M", page=page),
        lambda: get_monument_domain_card(db_session, tele_id, slot),
        db_session,
        tele_id,
    )
    if not out:
        await notify(cb, fail_text(DOMAIN))
        return
    sent, _ = out
    await cache_card(db_session, tele_id, sent, 'MONUD', data=str(slot), slot=slot)
    await ack(cb)


@rt.callback_query(F.data.startswith("back_M:"))
async def handle_back_monument(cb: CallbackQuery, db_session: AsyncSession):
    """Back from a domain card to the monument card , on the page we left."""
    checked = await check_cb(cb, 2)
    if not checked:
        return
    msg, (tele_id, page) = checked

    res = await get_monument_card(db_session, tele_id)
    if not res:
        await notify(cb, fail_text(MONUMENT))
        return

    out = await render(
        edit_sender(msg),
        res,
        lambda r: make_monument_kb(tele_id, domains=r.data, page=page),
        lambda: get_monument_card(db_session, tele_id),
        db_session,
        tele_id,
    )
    if not out:
        await notify(cb, fail_text(MONUMENT))
        return
    sent, res = out
    await cache_card(db_session, tele_id, sent, 'MONUA', data=dump_list(res.data))
    await _domains(db_session, tele_id).save(sent, tele_id, res.data)
    await ack(cb)
