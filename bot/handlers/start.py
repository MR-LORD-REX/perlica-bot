from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

rt=Router()

@rt.message(Command("start"))
async def start(msg:Message,db_session:AsyncSession):
    await msg.answer("hello")