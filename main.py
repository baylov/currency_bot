import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError

from config import settings
from utils.logger import setup_logging, get_logger
from handlers import router
from scheduler import setup_scheduler
from database import init_db


async def main() -> None:
    """Main function to initialize and start the bot."""
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        # Initialize bot
        bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Initialize dispatcher
        dp = Dispatcher()
        dp.include_router(router)
        
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Setup scheduler
        await setup_scheduler(bot)
        logger.info("Scheduler initialized successfully")
        
        # Start bot
        logger.info("Starting bot...")
        await dp.start_polling(bot)
        
    except TelegramAPIError as e:
        logger.error(f"Telegram API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Cleanup
        logger.info("Shutting down bot...")
        with suppress(Exception):
            if 'bot' in locals():
                await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")