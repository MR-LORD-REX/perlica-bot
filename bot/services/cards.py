from typing import List,Dict,Any,Union
from endfield_cards import EFCard
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from pydantic import BaseModel , ConfigDict
from PIL import Image
import ast

from bot.DB.repo.game_ids_repo import GameIDs_repo
from bot.DB.repo.user_setting_repo import UserSettingsRepo
from bot.DB.repo.cache_repo import CacheRepo

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
    
async def get_profile_card(session:AsyncSession,tele_id:int)->ProfileRes|None:
    uid=await GameIDs_repo(session).get_active_UID(tele_id)
    settings=await UserSettingsRepo(session).get_user_settings(tele_id)
    if not uid:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='PFP')
    card=None
    if cached:
        chars=ast.literal_eval(cached.data)
        return ProfileRes(
            cached=True,
            card=cached.file_id,
            data=chars
        )
    try:
        async with EFCard() as ef:
            card=await ef.get_profile_card(uid.game_id,template=settings.profile_template)
            chars=[]
            for c in card.characters:
                chars.append({"name":c.name,"slot":c.slot_index})
            return ProfileRes(
                cached=False,
                card=card.card,
                data=chars
            )
    except Exception as e:
        logging.error(f"error while generating profile card : {e}")
        return None
    
async def get_character_card(session:AsyncSession,tele_id:int,slot:int)-> CharRes|None:
    uid=await GameIDs_repo(session).get_active_UID(tele_id)
    settings=await UserSettingsRepo(session).get_user_settings(tele_id)
    if not uid:
        return None   
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='CHAR',slot=slot)
    card=None
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
        logging.error(f"error while generating profile card : {e}")
        return None