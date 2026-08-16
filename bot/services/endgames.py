from typing import List,Dict
from endfield_cards import EFCard
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from bot.DB.repo.game_ids_repo import GameIDs_repo
from bot.DB.repo.cache_repo import CacheRepo

from bot.utils.auth import decrypt_token
from bot.services.cards import ProfileRes , CharRes , load_list

logger=logging.getLogger(__name__)

# the monument showcase carries its domain list , same shape as a profile card
MonumentRes = ProfileRes
# a single domain card , same shape as a character card
DomainRes = CharRes

async def get_monument_card(
    session:AsyncSession,
    tele_id:int,
    ) -> MonumentRes|None:
    """Main monument template + the list of domains ( name , slot ) it shows."""
    user=await GameIDs_repo(session).get_active_UID(tele_id)
    if not user or not user.auth_token:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='MONUA')
    if cached:
        return MonumentRes(
            cached=True,
            card=cached.file_id,
            data=load_list(cached.data)
        )
    try:
        token=decrypt_token(user.auth_token)
        async with EFCard() as ef:
            res=await ef.get_monument_showcase_card(token)
            domains:List[Dict[str,str|int]]=[{"name":d.name,"slot":d.slot} for d in res.domains]
            return MonumentRes(
                cached=False,
                card=res.card,
                data=domains
            )
    except Exception as e:
        logger.error(f"error while generating monument card : {e}")
        return None

async def get_monument_domain_card(
    session:AsyncSession,
    tele_id:int,
    slot:int
    ) -> DomainRes|None:
    """Card of one monument domain , `slot` being its index in the showcase."""
    user=await GameIDs_repo(session).get_active_UID(tele_id)
    if not user or not user.auth_token:
        return None
    cached=await CacheRepo(session).get_cache(tele_id,cache_type='MONUD',slot=slot)
    if cached:
        return DomainRes(
            cached=True,
            card=cached.file_id,
            data=cached.data
        )
    try:
        token=decrypt_token(user.auth_token)
        async with EFCard() as ef:
            card=await ef.get_monument_domain_card(token,slot)
            return DomainRes(
                cached=False,
                card=card,
                data=str(slot)
            )
    except Exception as e:
        logger.error(f"error while generating monument domain card : {e}")
        return None
