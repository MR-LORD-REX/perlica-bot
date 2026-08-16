from abc import ABC, abstractmethod
import json
import logging
from typing import Optional, Dict, Any, List
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisInterface(ABC):
    """Abstract interface for Redis operations"""

    @abstractmethod
    async def set_session(self, key: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Store blueprint session data"""
        pass

    @abstractmethod
    async def get_session(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve blueprint session data"""
        pass

    @abstractmethod
    async def delete_session(self, key: str) -> bool:
        """Delete session data"""
        pass

    @abstractmethod
    async def exists_session(self, key: str) -> bool:
        """Check if session exists"""
        pass

    @abstractmethod
    async def update_session_page(self, key: str, page: int) -> bool:
        """Update current page in session"""
        pass


class BaseRedisStore(RedisInterface):
    """Generic json session storage on top of a redis client"""

    DEFAULT_TTL = 3600

    def __init__(self, client: redis.Redis):
        self.client = client

    async def set_session(self, key: str, data: Dict[str, Any], ttl: int = DEFAULT_TTL) -> bool:
        try:
            await self.client.setex(key, ttl if ttl > 0 else self.DEFAULT_TTL, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"error setting session {key}: {e}")
            return False

    async def get_session(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve and deserialize session data"""
        try:
            data = await self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"error getting session {key}: {e}")
            return None

    async def delete_session(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"error deleting session {key}: {e}")
            return False

    async def exists_session(self, key: str) -> bool:
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"error checking session {key}: {e}")
            return False

    async def update_session_page(self, key: str, page: int) -> bool:
        """Update current_page field in session , preserving the remaining ttl"""
        try:
            data = await self.get_session(key)
            if not data:
                return False
            data["current_page"] = page
            ttl = await self.client.ttl(key)
            return await self.set_session(key, data, ttl if ttl > 0 else self.DEFAULT_TTL)
        except Exception as e:
            logger.error(f"error updating page for {key}: {e}")
            return False


class BlueprintRedisStore(BaseRedisStore):
    """
    Blueprint pagination storage : bp_session:{chat_id}:{message_id}

    data = {
        "user_id": 123,
        "region": "Asia",
        "item_name": "xiranite",
        "current_page": 0,
        "total_pages": 5
    }
    """
    pass


class CardSessionStore(BaseRedisStore):
    """
    Item list storage for paginated card keyboards :
    {prefix}:{chat_id}:{message_id}

    data = {"user_id": 123, "items": [{"name": "...", ...}, ...]}

    The list is keyed by message so every card message paginates on its own ,
    and the inline buttons only need to carry a list index or a small id.
    """

    DEFAULT_TTL = 86400  # 1 day , outlives the shorter lived card cache

    def __init__(self, client: redis.Redis, prefix: str = "card_session"):
        super().__init__(client)
        self.prefix = prefix

    def make_key(self, chat_id: int, message_id: int) -> str:
        return f"{self.prefix}:{chat_id}:{message_id}"

    async def save_items(
        self,
        chat_id: int,
        message_id: int,
        user_id: int,
        items: List[Dict[str, Any]],
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        return await self.set_session(
            self.make_key(chat_id, message_id),
            {"user_id": user_id, "items": list(items)},
            ttl=ttl,
        )

    async def get_items(self, chat_id: int, message_id: int) -> Optional[List[Dict[str, Any]]]:
        data = await self.get_session(self.make_key(chat_id, message_id))
        if not data:
            return None
        items = data.get("items")
        return items if items else None
