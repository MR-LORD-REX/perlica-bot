from typing import Callable, Awaitable, Any
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import asyncio

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self)-> None:
        self.user_locks= defaultdict(asyncio.Lock)
    
    async def __call__(
        self,
        hander: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    )->Any:
        user_id=event.from_user.id
        lock=self.user_locks[user_id]
        async with lock:
            return await hander(event,data)
            