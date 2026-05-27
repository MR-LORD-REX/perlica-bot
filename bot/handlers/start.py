from aiogram import Router
from aiogram.types import Message , InlineKeyboardMarkup , InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.config import CHANNEL_LINK

rt=Router()



@rt.message(Command("start"))
async def start(msg: Message, db_session: AsyncSession):
    kb = InlineKeyboardBuilder()
    kb.button(text="Join our channel", url=CHANNEL_LINK)
    text = (
        "Welcome , Endministrator . I'm Perlica — Supervisor of Endfield Industries and your guide through Talos-II.\n\n"
        "Whether it's tracking your resin, checking factory output, or keeping tabs on your operators, "
        "I'll make sure things keep running smoothly on this end.\n\n"
        "Tap /help to see everything I can do for you.\n"
        "Join our channel below for the latest updates on the game and the bot."
    )
    await msg.reply(text, reply_markup=kb.as_markup(), parse_mode=None)
    
    
@rt.message(Command("help"))
async def help(msg: Message):
    text = (
        "Here are the commands you can use:\n\n"
        "/start - start the bot and see welcome message\n"
        "/help - see this message again\n"
        "/login - link your game account with the bot (UID required)\n"
        "/logout - unlink your game account from the bot\n"
        "/switch - switch between linked game accounts (if you have multiple)\n"
        "/token_login - link your account using token (for factory and notes access)\n"
        "/token_logout - unlink your endfield account from the bot\n"
        "/token_help - see instructions to get your token\n"
        "/myuid - see your linked game account UID\n"
        "/myc - see your profile cards\n"
        "/notes - see your live in-game notes (token required)\n"
        "/factory - see your factory status (token required)\n"
        "/settings - customize your preferences for reminders and character template\n"
        "/admin_help - see admin commands (admins and bot owner only)"
    )
    await msg.reply(text, parse_mode=None)
    
@rt.message(Command("token_help"))
async def token_help(msg: Message):
    kb=InlineKeyboardBuilder()
    kb.button(text="Join our channel",url=CHANNEL_LINK)
    text = (
        "Follow these steps to get your token:\n\n"
        "1. Open <a href='https://www.skport.com/'>official Endfield website</a> and log in with your game account.\n"
        "2. Come back to the bot.\n"
        "3. Go to this <a href='https://web-api.skport.com/cookie_store/account_token'>official Endfield API</a> and copy the token shown there without quotes.\n"
        "4. Use /token_login command and paste the token to link your account with the bot.\n"
        "5. You can now use token required commands like /notes and /factory.\n\n"
        "<b>Note:</b> Your token is sensitive information that can be used to access your game data."
        "Do not share it with anyone and only use it in this bot if you trust it.\n"
        "We use encryption and secure storage to protect your token.\n\n"
        "If you have any issues, please contact us in our support channel."
    )
    await msg.reply(text, parse_mode="HTML", reply_markup=kb.as_markup())