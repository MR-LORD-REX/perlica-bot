from sqlalchemy import Select 
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Generic ,Type , Sequence

from bot.DB.base import base

class BaseRepo(Generic[TypeVar("T", bound=base)]):
    def __init__(self, model: Type[base], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_all(self) -> Sequence[base]:
        result = await self.session.execute(Select(self.model))
        return result.scalars().all()
    
    async def add(self, obj: base) -> None:
        self.session.add(obj)
        await self.session.flush()
        
    async def delete(self, obj: base) -> None:
        await self.session.delete(obj)
        await self.session.flush()
        
    async def update(self, obj: base) -> None:
        self.session.add(obj)
        await self.session.flush()