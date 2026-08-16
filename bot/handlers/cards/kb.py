from typing import Literal , List , Dict , Sequence , Any
from math import ceil

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton , InlineKeyboardMarkup

CacheType = Literal['PFP','CHAR','MONUA','MONUD','ALLC','GAMEC']

PAGE_SIZE = 8  # item buttons per page ( 4 rows of 2 + nav row )
NOP_CB = "card_nop"  # page counter , answered by the shared card ui router

Items = Sequence[Dict[str,Any]]

def total_pages(items:Items,page_size:int=PAGE_SIZE)->int:
    return max(1, ceil(len(items) / page_size))

def clamp_page(page:int,pages:int)->int:
    return min(max(page, 0), pages - 1)

def make_report_keboard(tele_id:int , uid:int , r_type:CacheType='PFP') -> InlineKeyboardMarkup:
    kb=InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="report",callback_data=f"report:{r_type}:{tele_id}:{uid}"))
    return kb.as_markup()

def make_profile_keyboard(tele_id:int,chars:List[Dict[str,int]]) -> InlineKeyboardMarkup:
    kb=InlineKeyboardBuilder()
    for char in chars:
        kb.button(
            text=f"{char.get('name')}",
            callback_data=f"C_card:{tele_id}:{char.get('slot')}"
        )
    kb.adjust(2)
    return kb.as_markup()

def make_paged_kb(
    tele_id:int,
    items:Items,
    item_cb:str,
    page_cb:str,
    page:int=0,
    value_key:str|None=None,
    page_size:int=PAGE_SIZE,
    ) -> InlineKeyboardMarkup:
    """
    One page of item buttons with a `prev | n/N | next` nav row.

    item_cb   : prefix of an item button -> f"{item_cb}:{tele_id}:{page}:{value}"
    page_cb   : prefix of the nav buttons -> f"{page_cb}:{tele_id}:{page}"
    value_key : item field sent as `value` ; the list index is used when None ,
                which keeps the callback data short for long ids
    """
    pages=total_pages(items,page_size)
    page=clamp_page(page,pages)
    start=page*page_size

    kb=InlineKeyboardBuilder()
    for idx in range(start,min(start+page_size,len(items))):
        value=idx if value_key is None else items[idx].get(value_key)
        kb.button(
            text=f"{items[idx].get('name','?')}",
            callback_data=f"{item_cb}:{tele_id}:{page}:{value}"
        )
    kb.adjust(2)

    if pages>1:
        nav=[]
        if page>0:
            nav.append(InlineKeyboardButton(text="◀ prev",callback_data=f"{page_cb}:{tele_id}:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page+1}/{pages}",callback_data=NOP_CB))
        if page<pages-1:
            nav.append(InlineKeyboardButton(text="next ▶",callback_data=f"{page_cb}:{tele_id}:{page+1}"))
        kb.row(*nav)
    return kb.as_markup()

def make_allc_kb(tele_id:int,chars:Items,page:int=0) -> InlineKeyboardMarkup:
    """/allc characters ; buttons carry the list index , char_id is too long for callback data."""
    return make_paged_kb(tele_id,chars,item_cb="GAMEC",page_cb="allc_pg",page=page)

def make_monument_kb(tele_id:int,domains:Items,page:int=0) -> InlineKeyboardMarkup:
    """/monument domains ; buttons carry the domain slot."""
    return make_paged_kb(tele_id,domains,item_cb="MONUD",page_cb="monu_pg",page=page,value_key="slot")

def make_back_kb(tele_id:int,cb:str="back_P",page:int|None=None) -> InlineKeyboardMarkup:
    """
    Back button of a detail card.

    back_P:{tele_id}          -> /myc profile card
    back_A:{tele_id}:{page}   -> /allc card , on the page we left
    back_M:{tele_id}:{page}   -> /monument card , on the page we left
    """
    data=f"{cb}:{tele_id}" if page is None else f"{cb}:{tele_id}:{page}"
    kb=InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="back",callback_data=data))
    return kb.as_markup()
