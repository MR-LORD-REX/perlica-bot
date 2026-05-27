from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import asyncio

from bot.config.config import OWNER_TELE_ID
from bot.DB.repo.admin_repo import AdminRepo
from bot.DB.repo.tele_group_repo import TeleGroupRepo
from bot.DB.repo.user_repo import UserRepo

rt = Router()
logger = logging.getLogger(__name__)


def setup_admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="basic", callback_data="set_authority:basic"),
        InlineKeyboardButton(text="moderator", callback_data="set_authority:moderator")
    )
    kb.row(
        InlineKeyboardButton(text="admin", callback_data="set_authority:admin"),
        InlineKeyboardButton(text="owner", callback_data="set_authority:owner")
    )
    return kb.as_markup()


async def get_user_authority(db_session: AsyncSession, tele_id: int):
    if tele_id == OWNER_TELE_ID:
        return "owner"

    user = await AdminRepo(db_session).get_admin(tele_id)
    if not user:
        return None

    return user.authority


# ================================= OWNER ONLY COMMANDS =================================

@rt.message(Command("add_admin"))
async def add_admin(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    logger.info(f"add_admin command called by user {tele_id}")

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority != "owner":
        logger.warning(f"Unauthorized add_admin attempt: user {tele_id}")
        return

    target = message.reply_to_message if message.reply_to_message else None
    if not target:
        await message.reply("Please reply to the user to add as admin")
        return

    user_name = target.from_user.username if target.from_user.username else None
    display_name = target.from_user.full_name if target.from_user.full_name else None
    target_id = target.from_user.id

    await AdminRepo(db_session).add_admin(target_id, "basic")
    await db_session.commit()

    await message.reply(
        f"Admin added successfully with telegram id {target_id}, username {user_name}, display name {display_name}"
    )


@rt.message(Command("remove_admin"))
async def remove_admin(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    logger.info(f"remove_admin command called by user {tele_id}")

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority != "owner":
        logger.warning(f"Unauthorized remove_admin attempt: user {tele_id}")
        return

    target = message.reply_to_message if message.reply_to_message else None
    if not target:
        await message.reply("Please reply to the user to remove from admin")
        return

    target_id = target.from_user.id
    success = await AdminRepo(db_session).remove_admin(target_id)

    if success:
        await db_session.commit()
        await message.reply(f"Admin removed successfully with telegram id {target_id}")
    else:
        await message.reply(f"No admin found with telegram id {target_id}")


@rt.message(Command("update_admin"))
async def update_admin(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    logger.info(f"update_admin command called by user {tele_id}")

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority != "owner":
        logger.warning(f"Unauthorized update_admin attempt: user {tele_id}")
        return

    target = message.reply_to_message if message.reply_to_message else None
    if not target:
        await message.reply("Please reply to the user to update admin")
        return

    target_id = target.from_user.id
    target_user = await AdminRepo(db_session).get_admin(target_id)

    if not target_user:
        await message.reply(f"No admin found with telegram id {target_id}")
        return

    kb = setup_admin_kb()
    await message.reply(
        f"Select the authority level for the user with telegram id {target_id}",
        reply_markup=kb
    )


# ================================= ADMIN + OWNER =================================

@rt.message(Command("broadcast"))
async def broadcast(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    logger.info(f"broadcast command called by user {tele_id}")

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin"]:
        logger.warning(f"Unauthorized broadcast attempt: user {tele_id}")
        return

    to_send = message.reply_to_message.text if message.reply_to_message else message.text
    if not to_send:
        await message.reply("Please reply to the text message to broadcast")
        return

    from bot.core.main import bot

    groups = await TeleGroupRepo(db_session).get_all()

    for group in groups:
        try:
            await bot.send_message(group.group_id, to_send)
        except Exception as e:
            logger.error(f"Broadcast error in {group.group_id}: {e}")
            await asyncio.sleep(5)

    await message.reply("Broadcast sent successfully")


@rt.message(Command("broadcast_photo"))
async def broadcast_photo(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    logger.info(f"broadcast_photo command called by user {tele_id}")

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin"]:
        logger.warning(f"Unauthorized broadcast_photo attempt: user {tele_id}")
        return

    to_send = message.reply_to_message.photo if message.reply_to_message else message.photo
    if not to_send:
        await message.reply("Please reply to the photo to broadcast")
        return

    from bot.core.main import bot

    groups = await TeleGroupRepo(db_session).get_all()

    for group in groups:
        try:
            await bot.send_photo(group.group_id, to_send[-1].file_id)
        except Exception as e:
            logger.error(f"Broadcast photo error in {group.group_id}: {e}")
            await asyncio.sleep(5)

    await message.reply("Broadcast sent successfully")


# ================================= MODERATOR + ADMIN + OWNER =================================

@rt.message(Command("ban_user"))
async def ban_user(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin", "moderator"]:
        return

    if not message.reply_to_message:
        await message.reply("Please reply to the user to ban")
        return

    to_ban = message.reply_to_message.from_user.id
    await UserRepo(db_session).ban_user(to_ban)
    await db_session.commit()

    await message.reply("User banned successfully")


@rt.message(Command("unban_user"))
async def unban_user(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id

    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin", "moderator"]:
        return

    if not message.reply_to_message:
        await message.reply("Please reply to the user to unban")
        return

    to_unban = message.reply_to_message.from_user.id
    await UserRepo(db_session).unban_user(to_unban)
    await db_session.commit()

    await message.reply("User unbanned successfully")


# ================================= BASIC + ABOVE =================================

@rt.message(Command("send"))
async def send(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin", "moderator", "basic"]:
        return

    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.reply("Please enter the message to send")
        return

    to_send = parts[1]

    from bot.core.main import bot
    await bot.send_message(message.chat.id, to_send)


@rt.message(Command("reply"))
async def reply(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin", "moderator", "basic"]:
        return

    if not message.reply_to_message:
        await message.reply("please provide the user to reply to")
        return

    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.reply("please provide the text to reply")
        return

    await message.reply_to_message.reply(parts[1])


@rt.message(Command("delete"))
async def delete(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin", "moderator", "basic"]:
        return

    if not message.reply_to_message:
        await message.reply("Please reply to the message to delete")
        return

    from bot.core.main import bot

    try:
        await bot.delete_message(
            message.reply_to_message.chat.id,
            message.reply_to_message.message_id
        )
    except Exception:
        await message.reply("Error deleting message")


@rt.message(Command("admin_help"))
async def admin_help(message: Message, db_session: AsyncSession):
    tele_id = message.from_user.id
    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority not in ["owner", "admin", "moderator", "basic"]:
        return

    help_text = """
/add_admin - owner only
/remove_admin - owner only
/update_admin - owner only
/broadcast - admin + owner
/broadcast_photo - admin + owner
/ban_user - moderator + admin + owner
/unban_user - moderator + admin + owner
/send <message>
/reply <message>
/delete
"""

    await message.reply(help_text, parse_mode=None)


@rt.callback_query(F.data.startswith("set_authority:"))
async def set_authority(query: CallbackQuery, db_session: AsyncSession):
    tele_id = query.from_user.id
    user_authority = await get_user_authority(db_session, tele_id)

    if user_authority != "owner":
        return

    if not query.message.reply_to_message:
        await query.message.reply("No target user found")
        return

    target_id = query.message.reply_to_message.from_user.id
    target = await AdminRepo(db_session).get_admin(target_id)

    if not target:
        await query.message.reply("No admin found for the user")
        return

    new_authority = query.data.split(":")[1]

    await AdminRepo(db_session).update_admin(target.telegram_id, new_authority)
    await db_session.commit()

    await query.answer(
        f"Authority updated to {new_authority} for user with telegram id {target.telegram_id}",
        show_alert=True
    )