from aiogram.types import InlineKeyboardMarkup , InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_regions_keyboard(regions:list[str])->InlineKeyboardMarkup:
    kb=InlineKeyboardBuilder()
    for reg in regions:
        kb.button(text=reg,switch_inline_query_current_chat=f"bp:{reg}:")
    kb.adjust(2)
    return kb.as_markup()

def get_bp_kb(current:int, total:int, chat_id:int=None, msg_id:int=None)->InlineKeyboardMarkup:
    kb=InlineKeyboardBuilder()
    if not current==0:
        kb.button(text="◀ prev",callback_data=f"bps:{chat_id}:{msg_id}:{max(current-1,0)}")
    if not current==total-1:
        kb.button(text="next ▶",callback_data=f"bps:{chat_id}:{msg_id}:{min(current+1,total-1)}")
    return kb.as_markup()