from aiogram import Router
from aiogram.types import Message , CallbackQuery , InlineKeyboardMarkup 
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from bot.DB.repo.user_setting_repo import UserSettingsRepo
from bot.DB.repo.user_repo import UserRepo
from bot.DB.repo.game_ids_repo import GameIDs_repo


rt=Router()
logger=logging.getLogger(__name__)


def build_settings_keyboard(settings) -> InlineKeyboardMarkup:
    """Build inline keyboard for settings"""
    builder = InlineKeyboardBuilder()
    
    if settings:
        # Row 1: Daily Reminder | Weekly Reminder
        daily_state = "ON" if settings.dalies_reminder else "OFF"
        weekly_state = "ON" if settings.weekly_reminder else "OFF"
        builder.button(text=f"Daily Reminder: {daily_state}", callback_data="toggle_daily")
        builder.button(text=f"Weekly Reminder: {weekly_state}", callback_data="toggle_weekly")
        builder.adjust(2)
        
        # Row 2: Auto-Perform Daily
        perform_state = "ENABLED" if settings.perform_daily else "DISABLED"
        builder.button(text=f"Auto-Perform: {perform_state}", callback_data="toggle_perform")
        builder.adjust(1)
        
    return builder.as_markup()


@rt.message(Command("settings"))
async def settings(msg:Message,db_session:AsyncSession):
    tele_id=msg.from_user.id
    user=await UserRepo(db_session).get_by_tele_id(tele_id)
    if not user:
        await msg.reply("Please login using /login UID_NUMBER")
        return
    settings=await UserSettingsRepo(db_session).get_user_settings(tele_id)
    game_ids=await GameIDs_repo(db_session).get_UIDs(tele_id)
    active_game=await GameIDs_repo(db_session).get_active_UID(tele_id)
    
    # Build settings message
    text = "=" * 50 + "\n"
    text += "USER SETTINGS\n"
    text += "=" * 50 + "\n\n"
    
    # User info
    text += "[USER INFORMATION]\n"
    text += f"==> Username      : {user.username}\n"
    text += f"==> Display Name  : {user.display_name}\n"
    text += f"==> Status        : {'BANNED' if user.banned else 'ACTIVE'}\n"
    text += f"==> Warnings      : {user.warns}\n\n"
    
    # Game IDs
    text += "[GAME ACCOUNTS]\n"
    if game_ids:
        for idx, game in enumerate(game_ids, 1):
            status = "ACTIVE" if game.active else "inactive"
            text += f"  {idx}. Game ID: {game.game_id} || Status: {status}\n"
        text += f"\n==> Total Accounts: {len(game_ids)}\n"
        if active_game:
            text += f"==> Active Account: {active_game.game_id}\n"
    else:
        text += "  No game accounts linked\n"
    text += "\n"
    
    # User preferences
    text += "[PREFERENCES]\n"
    if settings:
        lang_map = {"en": "English", "zh": "Chinese", "jp": "Japanese"}
        text += f"==> Language          : {lang_map.get(settings.lang, settings.lang)}\n"
        text += f"==> Profile Template  : {settings.profile_template}\n"
        text += f"==> Character Template: {settings.character_template}\n"
        text += "\n"
        
        # Reminders section
        text += "[REMINDERS]\n"
        text += f"==> Daily Reminder    : {'ON' if settings.dalies_reminder else 'OFF'}\n"
        text += f"==> Weekly Reminder   : {'ON' if settings.weekly_reminder else 'OFF'}\n"
        text += "\n"
        
        # Daily performance
        text += "[DAILY TASKS]\n"
        text += f"==> Auto-Perform Daily: {'ENABLED' if settings.perform_daily else 'DISABLED'}\n"
    else:
        text += "No preferences saved yet\n"
    
    text += "\n" + "=" * 50
    
    keyboard = build_settings_keyboard(settings)
    await msg.reply(text, reply_markup=keyboard)


# Callback handlers for toggle options
@rt.callback_query(lambda c: c.data == "toggle_daily")
async def toggle_daily_reminder(callback: CallbackQuery, db_session: AsyncSession):
    tele_id = callback.from_user.id
    settings = await UserSettingsRepo(db_session).get_user_settings(tele_id)
    
    if settings:
        updated_settings = await UserSettingsRepo(db_session).change_user_settings(
            tele_id, 
            dalies_reminder=not settings.dalies_reminder
        )
        await db_session.commit()
        
        # Rebuild message with updated settings
        user = await UserRepo(db_session).get_by_tele_id(tele_id)
        game_ids = await GameIDs_repo(db_session).get_UIDs(tele_id)
        active_game = await GameIDs_repo(db_session).get_active_UID(tele_id)
        
        text = "=" * 50 + "\n"
        text += "USER SETTINGS\n"
        text += "=" * 50 + "\n\n"
        text += "[USER INFORMATION]\n"
        text += f"==> Username      : {user.username}\n"
        text += f"==> Display Name  : {user.display_name}\n"
        text += f"==> Status        : {'BANNED' if user.banned else 'ACTIVE'}\n"
        text += f"==> Warnings      : {user.warns}\n\n"
        text += "[GAME ACCOUNTS]\n"
        if game_ids:
            for idx, game in enumerate(game_ids, 1):
                status = "ACTIVE" if game.active else "inactive"
                text += f"  {idx}. Game ID: {game.game_id} || Status: {status}\n"
            text += f"\n==> Total Accounts: {len(game_ids)}\n"
            if active_game:
                text += f"==> Active Account: {active_game.game_id}\n"
        else:
            text += "  No game accounts linked\n"
        text += "\n"
        text += "[PREFERENCES]\n"
        lang_map = {"en": "English", "zh": "Chinese", "jp": "Japanese"}
        text += f"==> Language          : {lang_map.get(updated_settings.lang, updated_settings.lang)}\n"
        text += f"==> Profile Template  : {updated_settings.profile_template}\n"
        text += f"==> Character Template: {updated_settings.character_template}\n\n"
        text += "[REMINDERS]\n"
        text += f"==> Daily Reminder    : {'ON' if updated_settings.dalies_reminder else 'OFF'}\n"
        text += f"==> Weekly Reminder   : {'ON' if updated_settings.weekly_reminder else 'OFF'}\n\n"
        text += "[DAILY TASKS]\n"
        text += f"==> Auto-Perform Daily: {'ENABLED' if updated_settings.perform_daily else 'DISABLED'}\n"
        text += "\n" + "=" * 50
        
        keyboard = build_settings_keyboard(updated_settings)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Daily Reminder: {'turned ON' if updated_settings.dalies_reminder else 'turned OFF'}")
    else:
        await callback.answer("Settings not found")


@rt.callback_query(lambda c: c.data == "toggle_weekly")
async def toggle_weekly_reminder(callback: CallbackQuery, db_session: AsyncSession):
    tele_id = callback.from_user.id
    settings = await UserSettingsRepo(db_session).get_user_settings(tele_id)
    
    if settings:
        updated_settings = await UserSettingsRepo(db_session).change_user_settings(
            tele_id, 
            weekly_reminder=not settings.weekly_reminder
        )
        await db_session.commit()
        
        # Rebuild message with updated settings
        user = await UserRepo(db_session).get_by_tele_id(tele_id)
        game_ids = await GameIDs_repo(db_session).get_UIDs(tele_id)
        active_game = await GameIDs_repo(db_session).get_active_UID(tele_id)
        
        text = "=" * 50 + "\n"
        text += "USER SETTINGS\n"
        text += "=" * 50 + "\n\n"
        text += "[USER INFORMATION]\n"
        text += f"==> Username      : {user.username}\n"
        text += f"==> Display Name  : {user.display_name}\n"
        text += f"==> Status        : {'BANNED' if user.banned else 'ACTIVE'}\n"
        text += f"==> Warnings      : {user.warns}\n\n"
        text += "[GAME ACCOUNTS]\n"
        if game_ids:
            for idx, game in enumerate(game_ids, 1):
                status = "ACTIVE" if game.active else "inactive"
                text += f"  {idx}. Game ID: {game.game_id} || Status: {status}\n"
            text += f"\n==> Total Accounts: {len(game_ids)}\n"
            if active_game:
                text += f"==> Active Account: {active_game.game_id}\n"
        else:
            text += "  No game accounts linked\n"
        text += "\n"
        text += "[PREFERENCES]\n"
        lang_map = {"en": "English", "zh": "Chinese", "jp": "Japanese"}
        text += f"==> Language          : {lang_map.get(updated_settings.lang, updated_settings.lang)}\n"
        text += f"==> Profile Template  : {updated_settings.profile_template}\n"
        text += f"==> Character Template: {updated_settings.character_template}\n\n"
        text += "[REMINDERS]\n"
        text += f"==> Daily Reminder    : {'ON' if updated_settings.dalies_reminder else 'OFF'}\n"
        text += f"==> Weekly Reminder   : {'ON' if updated_settings.weekly_reminder else 'OFF'}\n\n"
        text += "[DAILY TASKS]\n"
        text += f"==> Auto-Perform Daily: {'ENABLED' if updated_settings.perform_daily else 'DISABLED'}\n"
        text += "\n" + "=" * 50
        
        keyboard = build_settings_keyboard(updated_settings)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Weekly Reminder: {'turned ON' if updated_settings.weekly_reminder else 'turned OFF'}")
    else:
        await callback.answer("Settings not found")


@rt.callback_query(lambda c: c.data == "toggle_perform")
async def toggle_perform_daily(callback: CallbackQuery, db_session: AsyncSession):
    tele_id = callback.from_user.id
    settings = await UserSettingsRepo(db_session).get_user_settings(tele_id)
    
    if settings:
        updated_settings = await UserSettingsRepo(db_session).change_user_settings(
            tele_id, 
            perform_daily=not settings.perform_daily
        )
        await db_session.commit()
        
        # Rebuild message with updated settings
        user = await UserRepo(db_session).get_by_tele_id(tele_id)
        game_ids = await GameIDs_repo(db_session).get_UIDs(tele_id)
        active_game = await GameIDs_repo(db_session).get_active_UID(tele_id)
        
        text = "=" * 50 + "\n"
        text += "USER SETTINGS\n"
        text += "=" * 50 + "\n\n"
        text += "[USER INFORMATION]\n"
        text += f"==> Username      : {user.username}\n"
        text += f"==> Display Name  : {user.display_name}\n"
        text += f"==> Status        : {'BANNED' if user.banned else 'ACTIVE'}\n"
        text += f"==> Warnings      : {user.warns}\n\n"
        text += "[GAME ACCOUNTS]\n"
        if game_ids:
            for idx, game in enumerate(game_ids, 1):
                status = "ACTIVE" if game.active else "inactive"
                text += f"  {idx}. Game ID: {game.game_id} || Status: {status}\n"
            text += f"\n==> Total Accounts: {len(game_ids)}\n"
            if active_game:
                text += f"==> Active Account: {active_game.game_id}\n"
        else:
            text += "  No game accounts linked\n"
        text += "\n"
        text += "[PREFERENCES]\n"
        lang_map = {"en": "English", "zh": "Chinese", "jp": "Japanese"}
        text += f"==> Language          : {lang_map.get(updated_settings.lang, updated_settings.lang)}\n"
        text += f"==> Profile Template  : {updated_settings.profile_template}\n"
        text += f"==> Character Template: {updated_settings.character_template}\n\n"
        text += "[REMINDERS]\n"
        text += f"==> Daily Reminder    : {'ON' if updated_settings.dalies_reminder else 'OFF'}\n"
        text += f"==> Weekly Reminder   : {'ON' if updated_settings.weekly_reminder else 'OFF'}\n\n"
        text += "[DAILY TASKS]\n"
        text += f"==> Auto-Perform Daily: {'ENABLED' if updated_settings.perform_daily else 'DISABLED'}\n"
        text += "\n" + "=" * 50
        
        keyboard = build_settings_keyboard(updated_settings)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Auto-Perform Daily: {'ENABLED' if updated_settings.perform_daily else 'DISABLED'}")
    else:
        await callback.answer("Settings not found")

    