import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from sqlalchemy import select, func

from app.config import settings
from app.database.database import init_db, async_session_factory
from app.database.models import Product
from app.middlewares.db_session import DbSessionMiddleware
from app.middlewares.error_middleware import ErrorHandlingMiddleware
from app.handlers import (
    start,
    profile,
    catalog,
    cart,
    orders,
    search,
    admin,
    manager_orders,
)

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Register Middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(ErrorHandlingMiddleware())

    # Register Handlers/Routers
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(admin.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(orders.router)
    dp.include_router(search.router)
    dp.include_router(manager_orders.router)

    return dp


async def auto_seed_products_if_empty() -> None:
    async with async_session_factory() as session:
        count = await session.scalar(select(func.count(Product.id))) or 0
        if count == 0:
            logger.info("Database is empty. Attempting auto-import of products from price list...")
            candidate_paths = [
                os.path.join(os.path.dirname(__file__), "price_default.xls"),
                os.path.join("data", "price.xls"),
                settings.DEFAULT_PRICE_PATH,
            ]
            for path in candidate_paths:
                if os.path.exists(path):
                    logger.info(f"Found price list at: {path}. Importing...")
                    try:
                        from scripts.import_products import import_products_from_excel
                        await import_products_from_excel(path)
                        break
                    except Exception as e:
                        logger.error(f"Failed auto-importing from {path}: {e}")


async def healthcheck_handler(request: web.Request) -> web.Response:
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TOYO Wholesale Bot Status</title>
        <meta charset="utf-8">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .card { background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 450px; border: 1px solid #334155; }
            .status { display: inline-flex; align-items: center; background: #065f46; color: #34d399; padding: 0.4rem 1rem; border-radius: 9999px; font-weight: 600; margin-bottom: 1.5rem; }
            .dot { width: 10px; height: 10px; background: #10b981; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
            h1 { margin: 0 0 0.5rem 0; font-size: 1.75rem; color: #38bdf8; }
            p { color: #94a3b8; line-height: 1.5; margin: 0 0 1.5rem 0; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="status"><div class="dot"></div> BOT IS ONLINE 24/7</div>
            <h1>🛢 TOYO Wholesale Bot</h1>
            <p>Telegram-бот оптового заказа моторных масел работает в штатном режиме.</p>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def start_web_server() -> web.AppRunner:
    port = int(os.environ.get("PORT", "7860"))
    app = web.Application()
    app.router.add_get("/", healthcheck_handler)
    app.router.add_get("/health", healthcheck_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health status web server listening on http://0.0.0.0:{port}")
    return runner


async def start_bot() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Initializing database...")
    await init_db()
    await auto_seed_products_if_empty()

    bot = create_bot()
    dp = create_dispatcher()

    runner = None
    try:
        runner = await start_web_server()
    except Exception as e:
        logger.warning(f"Could not start web server on port 7860: {e}")

    logger.info("Starting Telegram Bot polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        if runner:
            await runner.cleanup()
        await bot.session.close()
