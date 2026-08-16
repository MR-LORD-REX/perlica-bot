from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, BIGINT, ForeignKey , Enum , Index
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column


from bot.DB.base import base

class GameID(base):
    __tablename__ = "game_ids"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    game_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    auth_token:Mapped[str]=mapped_column(String,nullable=True)
    skport_id:Mapped[int]=mapped_column(BIGINT,nullable=True)
    skport_name:Mapped[str]=mapped_column(String,nullable=True)
    server_id:Mapped[int]=mapped_column(Integer,nullable=True)
    sk_role:Mapped[str]=mapped_column(String,nullable=True)
    
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    user = relationship("Users", back_populates="game_ids")
    __table_args__ = (Index("one_active_idx", "user_id", "game_id"
        , unique=True, postgresql_where=(active == True)),)