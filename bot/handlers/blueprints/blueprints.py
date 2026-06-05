from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.blueprints import ITEMS_INFO, fetch_blueprint, format_blueprint_caption
from bot.redis_store import redis_connector, BlueprintRedisStore

from .kb import get_regions_keyboard , get_bp_kb

rt= Router()


@rt.message(Command("blueprints"))
async def blueprints_handler(message:Message,db_session:AsyncSession):
    kb=get_regions_keyboard(["Asia", "Americas/Europe", "Both"])
    await message.reply("Please select the region:\n\nStart writing the name of an item for suggetions",reply_markup=kb)
    
@rt.inline_query(F.query.startswith("bp:"))
async def handle_bp_region(inline_query: InlineQuery):
    result=[]
    # Parse region and search: "bp:RegionName:SearchTerm"
    parts = inline_query.query.split(":", 2)
    if len(parts) < 2:
        return inline_query.answer(results=[], cache_time=5)
    
    region = parts[1]
    search = parts[2].strip().lower() if len(parts) > 2 else ""
    
    matches=[]
    for bp in ITEMS_INFO.values():
        name=bp["name"]
        if not search or search in name.lower():
            matches.append(bp)
    
    for bp in matches[:50]:
        id=bp["id"]
        name=bp["name"]
        icon=bp["icon_url"]
        result.append(
            InlineQueryResultArticle(
                id=id,
                title=name,
                description=f"view blueprints of {name}",
                thumbnail_url=icon,
                thumbnail_width=100,
                thumbnail_height=100,
                input_message_content=InputTextMessageContent(
                    message_text=f"/bps {region}:{name}"
                )
            )
        )
    return inline_query.answer(results=result,cache_time=30, is_personal=True)

@rt.message(F.text.startswith("/bps "))
async def handle_blueprint_show(msg:Message):
    parts = msg.text[len("/bps "):].split(":")
    if len(parts) != 2:
        await msg.reply("Invalid format. Use: /bps Region:ItemName\nExample: /bps Asia:amethyst-bottle")
        return
    
    server = parts[0].strip()
    name = parts[1].strip()
    
    if not server or not name:
        await msg.reply("Region and item name cannot be empty")
        return
    
    try:
        blueprint, total = await fetch_blueprint(server, name, 0)
        
        if not blueprint:
            await msg.reply(text="No matching blueprints found")
            return
        
        # Store session in Redis
        client = redis_connector.get_client()
        store = BlueprintRedisStore(client)
        
        # Create placeholder message to get message_id
        placeholder = await msg.reply("Loading blueprint...")
        
        session_key = f"bp_session:{msg.chat.id}:{placeholder.message_id}"
        session_data = {
            "user_id": msg.from_user.id,
            "region": server,
            "item_name": name,
            "current_page": 0,
            "total_pages": total
        }
        await store.set_session(session_key, session_data, ttl=3600)
        
        caption = format_blueprint_caption(blueprint, page=0, total_pages=total)
        icon = blueprint.screenshot_url
        
        await placeholder.delete()
        sent_msg = await msg.reply_photo(photo=icon, caption=caption, reply_markup=get_bp_kb(current=0, total=total, chat_id=msg.chat.id, msg_id=placeholder.message_id))
        
        # Update session with actual message_id
        session_key = f"bp_session:{msg.chat.id}:{sent_msg.message_id}"
        await store.set_session(session_key, session_data, ttl=3600)
        
    except Exception as e:
        print(f"Error: {e}")
        await msg.reply("An error occurred while fetching blueprints")


@rt.callback_query(F.data.startswith("bps:"))
async def handle_pagination(callback: CallbackQuery):
    try:
        # Parse callback data: bps:chat_id:msg_id:page
        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer("Invalid callback data", show_alert=True)
            return
        
        chat_id = int(parts[1])
        msg_id = int(parts[2])
        page = int(parts[3])

        is_private = callback.message.chat.type == "private"
        
        if callback.message.chat.id != chat_id:
            await callback.answer("This button is for a different chat", show_alert=True)
            return
        
        if not is_private and callback.message.message_id != msg_id:
            await callback.answer("This button is for a different message", show_alert=True)
            return
        
        client = redis_connector.get_client()
        store = BlueprintRedisStore(client)
        session_key = f"bp_session:{chat_id}:{msg_id}"
        session = await store.get_session(session_key)
        
        if not session:
            await callback.answer("Session expired", show_alert=True)
            return

        if session["user_id"] != callback.from_user.id:
            await callback.answer("Only the user who started this can use buttons", show_alert=True)
            return

        region = session["region"]
        item_name = session["item_name"]
        total = session["total_pages"]
        
        if page < 0 or page >= total:
            await callback.answer("Invalid page", show_alert=True)
            return
        
        try:
            blueprint, _ = await fetch_blueprint(region, item_name, page)
            
            if not blueprint:
                await callback.answer("Blueprint not found", show_alert=True)
                return
            
            caption = format_blueprint_caption(blueprint, page=page, total_pages=total)
            icon = blueprint.screenshot_url
            
            await store.update_session_page(session_key, page)
            kb = get_bp_kb(current=page, total=total, chat_id=chat_id, msg_id=msg_id)

            await callback.message.edit_media(
                InputMediaPhoto(media=icon, caption=caption),
                reply_markup=kb
            )
            await callback.answer()
            
        except Exception as e:
            print(f"Error fetching blueprint: {e}")
            await callback.answer(f"Error: {str(e)}", show_alert=True)
    
    except Exception as e:
        print(f"Error in pagination handler: {e}")
        await callback.answer("An error occurred", show_alert=True)