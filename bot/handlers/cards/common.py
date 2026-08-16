"""
Shared plumbing for card handlers ( /myc , /allc , /monument ).

The flow of every card command is the same :

    guard the user  ->  build / fetch the card  ->  send or edit it
                    ->  cache the telegram file_id  ->  answer the callback

`render` and `cache_card` cover the send + cache half , the `cb_*` helpers cover
callback validation , and `PagedSession` keeps the item list a paginated keyboard
was built from in redis.
"""
from typing import Awaitable, Callable, List, Dict, Any, TypeVar
import logging

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    ReactionTypeEmoji,
    BufferedInputFile,
)
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.auth import check_user
from bot.services.cards import ProfileRes, CharRes
from bot.utils.images import image_to_tgFile
from bot.handlers.cards.kb import CacheType, NOP_CB

from bot.DB.repo.game_ids_repo import GameIDs_repo
from bot.DB.repo.cache_repo import CacheRepo
from bot.redis_store import redis_connector, CardSessionStore

logger = logging.getLogger(__name__)

# shared card ui router , included from bot.handlers.routers
rt = Router()

CardRes = ProfileRes | CharRes
# a card keeps its own type through `render` : a monument stays a MonumentRes ,
# so `res.data` is still the domain list and not "list or str"
ResT = TypeVar("ResT", ProfileRes, CharRes)
Photo = str | BufferedInputFile
Sender = Callable[[Photo, InlineKeyboardMarkup], Awaitable[Message | bool]]
Notify = Callable[[str], Awaitable[Any]]
Items = List[Dict[str, Any]]

LOGIN_PROMPT = "please login using /login or /switch "
TOKEN_PROMPT = "please login with /token_login , use /token_help for more info"
LIST_EXPIRED = "this list is no longer available , run the command again"

# telegram rejects a file_id that no longer resolves ; those cards get rebuilt
STALE_MEDIA_ERRORS = (
    "wrong file identifier",
    "wrong remote file identifier",
    "media_empty",
)


def fail_text(card: str) -> str:
    return (
        f"failed to generate {card} card , "
        "press report to report the issue to the bot admins "
    )


# ------------------------------------------------------------------ guards ----

async def react(msg: Message, emoji: str = "👍") -> None:
    try:
        await msg.react([ReactionTypeEmoji(emoji=emoji)])
    except Exception as e:
        logger.warning(f"could not react to message: {e}")


async def active_uid(
    db_session: AsyncSession,
    tele_id: int,
    notify: Notify,
    need_token: bool = False,
):
    """Active game UID for the user , or None after telling them what to do."""
    user = await check_user(db_session, tele_id)
    uid = await GameIDs_repo(db_session).get_active_UID(tele_id)
    if not user or not uid:
        await notify(LOGIN_PROMPT)
        return None
    if need_token and not uid.auth_token:
        await notify(TOKEN_PROMPT)
        return None
    return uid


# ---------------------------------------------------------------- callback ----

async def ack(cb: CallbackQuery) -> None:
    """Clear the button's loading state , tolerating an expired query id."""
    try:
        await cb.answer()
    except TelegramBadRequest as e:
        logger.debug(f"could not answer callback query: {e}")


async def notify(cb: CallbackQuery, text: str) -> None:
    """
    Report a problem to the user.

    Building a card can outlive the callback query , in which case the alert is
    refused by telegram and the message is sent as a reply instead.
    """
    try:
        await cb.answer(text, show_alert=True)
        return
    except TelegramBadRequest as e:
        logger.debug(f"callback query expired ({e}) , replying instead")
    if not isinstance(cb.message, Message):
        return
    try:
        await cb.message.reply(text)
    except TelegramBadRequest as e:
        logger.warning(f"could not notify {cb.from_user.id}: {e}")


def cb_ints(cb: CallbackQuery, count: int) -> List[int] | None:
    """The `count` int arguments of `prefix:a:b:...` , or None when malformed."""
    parts = (cb.data or "").split(":")[1:]
    if len(parts) < count:
        return None
    try:
        return [int(p) for p in parts[:count]]
    except ValueError:
        return None


async def check_cb(cb: CallbackQuery, count: int) -> tuple[Message, List[int]] | None:
    """
    Validate a callback : parseable , editable message , pressed by its owner.

    Returns the message the buttons live on together with the `count` int
    arguments , the first of which is always the owner's telegram id.
    """
    args = cb_ints(cb, count)
    if not args:
        logger.warning(f"malformed callback data: {cb.data}")
        await notify(cb, "broken button , please run the command again")
        return None
    if not isinstance(cb.message, Message):
        await notify(cb, "this message is too old to update")
        return None
    if cb.from_user.id != args[0]:
        await notify(cb, "not for you")
        return None
    return cb.message, args


# ------------------------------------------------------------------ sending ----

def _is_stale_media(err: TelegramBadRequest) -> bool:
    text = str(err).lower()
    return any(marker in text for marker in STALE_MEDIA_ERRORS)


async def photo(res: CardRes) -> Photo:
    """Reuse the cached telegram file_id when there is one , else upload the image."""
    if res.cached and isinstance(res.card, str) and res.card:
        return res.card
    return await image_to_tgFile(res.card)


def reply_sender(msg: Message) -> Sender:
    """Send the card as a reply to a command."""
    return lambda ph, kb: msg.reply_photo(photo=ph, reply_markup=kb)


def edit_sender(msg: Message) -> Sender:
    """Replace the card of a message a button was pressed on."""
    return lambda ph, kb: msg.edit_media(
        media=InputMediaPhoto(media=ph), reply_markup=kb
    )


async def render(
    send: Sender,
    res: ResT,
    keyboard: Callable[[ResT], InlineKeyboardMarkup],
    regenerate: Callable[[], Awaitable[ResT | None]],
    db_session: AsyncSession,
    tele_id: int,
) -> tuple[Message, ResT] | None:
    """
    Send / edit a card and return the resulting message with the card actually used.

    A cached file_id telegram no longer accepts is dropped from the cache and the
    card is rebuilt once ; None means the card could not be delivered.
    """
    try:
        sent = await send(await photo(res), keyboard(res))
        return (sent, res) if isinstance(sent, Message) else None
    except TelegramBadRequest as e:
        if not _is_stale_media(e):
            raise
        logger.warning(f"stale cached file_id for {tele_id} , regenerating card: {e}")

    await CacheRepo(db_session).delete_all_cache(tele_id)
    fresh = await regenerate()
    if not fresh:
        return None
    sent = await send(await photo(fresh), keyboard(fresh))
    return (sent, fresh) if isinstance(sent, Message) else None


async def cache_card(
    db_session: AsyncSession,
    tele_id: int,
    sent: Message,
    cache_type: CacheType,
    data: str | None,
    slot: int | None = None,
    char_id: str | None = None,
) -> None:
    """Store the largest photo size's file_id so the next call can skip rendering."""
    if not sent.photo:
        logger.warning(f"no photo on {cache_type} message for {tele_id} , not caching")
        return
    await CacheRepo(db_session).set_cache(
        tele_id,
        sent.photo[-1].file_id,
        cache_type=cache_type,
        data=data,
        slot=slot,
        char_id=char_id,
    )
    await db_session.commit()


# ---------------------------------------------------------- paged sessions ----

class PagedSession:
    """
    The item list a paginated keyboard was built from , kept in redis per message.

    Redis is optional : without it ( or once the session expires ) the list is
    rebuilt through `fetch` , which reads the card cache.
    """

    def __init__(self, prefix: str, fetch: Callable[[], Awaitable[Items | None]]):
        self.prefix = prefix
        self.fetch = fetch

    def _store(self) -> CardSessionStore | None:
        try:
            return CardSessionStore(redis_connector.get_client(), prefix=self.prefix)
        except Exception as e:
            logger.warning(f"redis unavailable for {self.prefix} sessions: {e}")
            return None

    async def save(self, msg: Message, tele_id: int, items: Items) -> None:
        store = self._store()
        if store:
            await store.save_items(msg.chat.id, msg.message_id, tele_id, items)

    async def load(self, msg: Message, tele_id: int) -> Items | None:
        store = self._store()
        if store:
            items = await store.get_items(msg.chat.id, msg.message_id)
            if items:
                return items
        items = await self.fetch()
        if not items:
            return None
        if store:
            await store.save_items(msg.chat.id, msg.message_id, tele_id, items)
        return items


@rt.callback_query(F.data == NOP_CB)
async def handle_nop(cb: CallbackQuery):
    """Page counter button , shared by every paginated card keyboard."""
    await ack(cb)
