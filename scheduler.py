from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Optional

from aiogram import Bot
from config import settings
from api_client import get_crypto_prices, APIError
from utils.logger import get_logger

logger = get_logger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def setup_scheduler(bot: Bot) -> None:
    """Initialize and configure the APScheduler."""
    global scheduler
    
    scheduler = AsyncIOScheduler(
        timezone=settings.scheduler_timezone,
        max_workers=settings.scheduler_max_workers,
    )
    
    # Add example jobs (you can remove or modify these)
    await add_example_jobs(bot)
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started successfully")


async def add_example_jobs(bot: Bot) -> None:
    """Add example scheduled jobs."""
    
    # Example: Send a daily message at 9:00 AM
    scheduler.add_job(
        send_daily_message,
        trigger=CronTrigger(hour=9, minute=0),
        args=[bot],
        id="daily_message",
        name="Daily message",
        replace_existing=True,
    )
    
    # Example: Send a message every 30 minutes
    scheduler.add_job(
        send_periodic_message,
        trigger=IntervalTrigger(minutes=30),
        args=[bot],
        id="periodic_message",
        name="Periodic message",
        replace_existing=True,
    )
    
    logger.info("Example jobs added to scheduler")


async def send_daily_message(bot: Bot) -> None:
    """Example job: Send a daily message."""
    try:
        # This is just an example - in a real bot you'd send to actual users
        logger.info("Daily message job executed")
        # await bot.send_message(chat_id=ADMIN_CHAT_ID, text="Good morning! ☀️")
    except Exception as e:
        logger.error(f"Error in daily message job: {e}")


async def send_periodic_message(bot: Bot) -> None:
    """Example job: Send a periodic message."""
    try:
        logger.info("Periodic message job executed")
        # await bot.send_message(chat_id=ADMIN_CHAT_ID, text="Periodic check-in! 🔄")
    except Exception as e:
        logger.error(f"Error in periodic message job: {e}")


async def send_price_update(bot: Bot, chat_id: int) -> None:
    """Example job: Send cryptocurrency price update.
    
    This demonstrates how to use the API client in scheduled jobs.
    Usage: scheduler.add_job(send_price_update, ..., args=[bot, chat_id])
    """
    try:
        logger.info("Fetching cryptocurrency prices for scheduled update")
        
        prices = await get_crypto_prices()
        
        message = (
            f"📊 <b>Price Update ({prices['currency']})</b>\n\n"
            f"₿ Bitcoin: {prices['btc']:,.2f} ₽\n"
            f"Ξ Ethereum: {prices['eth']:,.2f} ₽\n"
            f"₮ Tether: {prices['usdt']:.2f} ₽\n"
        )
        
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
        logger.info(f"Price update sent to chat {chat_id}")
        
    except APIError as e:
        logger.error(f"API error in price update job: {e}")
    except Exception as e:
        logger.error(f"Error in price update job: {e}", exc_info=True)


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance."""
    return scheduler