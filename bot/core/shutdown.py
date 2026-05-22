from bot.DB.engine import engine

async def on_shutdown():
    await engine.dispose()