import asyncio
import sys
from app.bot import start_bot

if __name__ == "__main__":
    if sys.platform == "win32":
        # Ensure proper asyncio event loop policy on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
