from typing import List,Dict,Any,Union
from endfield_cards import EFCard
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from pydantic import BaseModel , ConfigDict
from PIL import Image
import ast
import json

from bot.DB.repo.game_ids_repo import GameIDs_repo
from bot.DB.repo.user_setting_repo import UserSettingsRepo
from bot.DB.repo.cache_repo import CacheRepo

from bot.utils.auth import encrypt_token , decrypt_token

logger=logging.getLogger(__name__)

class ProfileRes(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cached:bool
    card:str| Image.Image
    data: List[Dict[str,str|int]]

class CharRes(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    cached:bool
    card:str| Image.Image
    data: str|None

def dump_list(items:List[Dict[str,Any]])->str:
    """Serialize a list of items ( characters , domains ) for the `cache.data` column."""
    return json.dumps(items)

def load_list(raw:str|None)->List[Dict[str,Any]]:
    """Read back such a list , tolerating rows written as a python repr."""
    if not raw:
        return []
    try:
        items=json.loads(raw)
    except (TypeError,ValueError):
        try:
            items=ast.literal_eval(raw)
        except (ValueError,SyntaxError) as e:
            logger.warning(f"unreadable cached list : {e}")
            return []
    return items if isinstance(items,list) else []

async def get_profile_card(session:AsyncSession,tele_id:int)->ProfileRes|None:
    uid=await GameIDs_repo(session).get_active_UID(tele_id)
    settings=await UserSettingsRepo(session).get_user_settings(tele_id)
    if not uid:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='PFP')
    if cached:
        return ProfileRes(
            cached=True,
            card=cached.file_id,
            data=load_list(cached.data)
        )
    try:
        async with EFCard() as ef:
            card=await ef.get_profile_card(uid.game_id,template=settings.profile_template)
            chars=[{"name":c.name,"slot":c.slot_index} for c in card.characters]
            return ProfileRes(
                cached=False,
                card=card.card,
                data=chars
            )
    except Exception as e:
        logger.error(f"error while generating profile card : {e}")
        return None

async def get_character_card(session:AsyncSession,tele_id:int,slot:int)-> CharRes|None:
    uid=await GameIDs_repo(session).get_active_UID(tele_id)
    settings=await UserSettingsRepo(session).get_user_settings(tele_id)
    if not uid:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='CHAR',slot=slot)
    if cached:
        return CharRes(
            cached=True,
            card=cached.file_id,
            data=cached.data
        )
    try:
        async with EFCard() as ef:
            card=await ef.get_character_card(uid.game_id,slot,template=settings.character_template)
            return CharRes(
                cached=False,
                card=card,
                data=str(slot)
            )
    except Exception as e:
        logger.error(f"error while generating character card : {e}")
        return None

async def get_allc_card(
    session:AsyncSession,
    tele_id:int,
    ) -> ProfileRes|None:
    user=await GameIDs_repo(session).get_active_UID(tele_id)
    if not user or not user.auth_token:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='ALLC')
    if cached:
        return ProfileRes(
            cached=True,
            card=cached.file_id,
            data=load_list(cached.data)
        )
    try:
        token=decrypt_token(user.auth_token)
        async with EFCard() as ef:
            res=await ef.get_allc_card(token)
            chars:List[Dict[str,str|int]]=[{"name":c.name,"char_id":c.char_id} for c in res.allChars.characters]
            return ProfileRes(
                cached=False,
                card=res.card,
                data=chars
            )
    except Exception as e:
        logger.error(f"error while generating allc card : {e}")
        return None

async def get_game_char(
    session:AsyncSession,
    tele_id:int,
    char_id:str
    ) -> CharRes|None:
    user=await GameIDs_repo(session).get_active_UID(tele_id)
    if not user or not user.auth_token:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='GAMEC',char_id=char_id)
    if cached:
        return CharRes(
            cached=True,
            card=cached.file_id,
            data=str(char_id)
        )
    try:
        token=decrypt_token(user.auth_token)
        async with EFCard() as ef:
            card=await ef.get_game_character(token,char_id)
            return CharRes(
                cached=False,
                card=card,
                data=str(char_id)
            )
    except Exception as e:
        logger.error(f"error while generating game character card : {e}")
        return None
