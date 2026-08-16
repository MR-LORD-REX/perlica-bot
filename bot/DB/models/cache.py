from __future__ import annotations

from sqlalchemy import Column, Integer, String , Boolean , BIGINT , ForeignKey , Text, Enum , Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import DateTime
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy import UniqueConstraint

from bot.DB.base import base

class Cache(base):
    __tablename__='cache'

    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    telegram_id:Mapped[int]=mapped_column(BIGINT,ForeignKey('users.telegram_id'))
    file_id:Mapped[str]=mapped_column(String(255))
    data:Mapped[str]=mapped_column(Text, nullable=True)
    slot:Mapped[int]=mapped_column(Integer,nullable=True)
    char_id:Mapped[str]=mapped_column(String(255),nullable=True)
    type:Mapped[str]=mapped_column(Enum('PFP','CHAR','MONUA','MONUD','ALLC','GAMEC',name='cache_type'))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped["Users"] = relationship("Users", back_populates="cache")
    
    __table_args__ = (
        # slot keyed types : one row per character slot / monument domain
        Index(
            'uq_cache_slot',
            'telegram_id', 'type', 'slot',
            unique=True,
            postgresql_where=(Column('type').in_(['CHAR', 'MONUD'])),
        ),
        # game characters are cached per hashed char_id , one row per character
        Index(
            'uq_cache_gamec',
            'telegram_id', 'type', 'char_id',
            unique=True,
            postgresql_where=(Column('type') == 'GAMEC'),
        ),
        # every other type is a single card per user
        Index(
            'uq_cache_single',
            'telegram_id', 'type',
            unique=True,
            postgresql_where=(Column('type').notin_(['CHAR', 'MONUD', 'GAMEC'])),
        ),
    )
    