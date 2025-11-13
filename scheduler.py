import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from aiogram import Bot
from config import settings
from api_client import get_crypto_prices, APIError, APITimeoutError, APIRateLimitError
from database_alerts import AlertRepository
from database import AlertStatus, AlertDirection
from localization import localization
from utils.logger import get_logger

logger = get_logger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

# Lock to prevent concurrent alert checking
_alert_check_lock = asyncio.Lock()


async def setup_scheduler(bot: Bot) -> None:
    """Initialize and configure the APScheduler."""
    global scheduler
    
    scheduler = AsyncIOScheduler(
        timezone=settings.scheduler_timezone,
        max_workers=settings.scheduler_max_workers,
    )
    
    # Add the price check job to run every 5 minutes
    scheduler.add_job(
        check_and_notify_alerts,
        trigger=IntervalTrigger(minutes=5),
        args=[bot],
        id="price_alert_checker",
        name="Price Alert Checker",
        replace_existing=True,
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started successfully with price alert checker job")


async def check_and_notify_alerts(bot: Bot) -> None:
    """
    Main scheduler job: Fetch prices, check alerts, and send notifications.
    
    This job runs every 5 minutes and:
    1. Fetches current cryptocurrency prices
    2. Retrieves all active alerts
    3. Compares prices against alert thresholds
    4. Sends notifications for triggered alerts
    5. Updates alert status to TRIGGERED
    """
    # Prevent concurrent execution
    async with _alert_check_lock:
        try:
            logger.info("Starting price alert check cycle")
            
            # Step 1: Fetch current prices with retry logic
            prices = await fetch_prices_with_retry(max_retries=settings.api_max_retries)
            if prices is None:
                logger.warning("Failed to fetch prices - skipping this check cycle")
                return
            
            logger.info(
                f"Current prices: BTC={prices['btc']:.2f}, "
                f"ETH={prices['eth']:.2f}, USDT={prices['usdt']:.2f}"
            )
            
            # Step 2: Get all active alerts
            active_alerts = await AlertRepository.list_active_alerts()
            logger.info(f"Found {len(active_alerts)} active alerts to check")
            
            if not active_alerts:
                logger.debug("No active alerts to process")
                return
            
            # Step 3: Check each alert and collect triggered ones
            triggered_alerts = await check_alerts_against_prices(active_alerts, prices)
            logger.info(f"Found {len(triggered_alerts)} triggered alerts")
            
            # Step 4: Send notifications for triggered alerts
            if triggered_alerts:
                await send_alert_notifications(bot, triggered_alerts)
            
            logger.info("Price alert check cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in price alert check cycle: {e}", exc_info=True)


async def fetch_prices_with_retry(max_retries: int = 3) -> Optional[Dict]:
    """
    Fetch cryptocurrency prices with retry logic.
    
    Args:
        max_retries: Maximum number of retries
        
    Returns:
        Price data dictionary or None if all retries failed
    """
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            logger.info(f"Fetching prices (attempt {retry_count + 1}/{max_retries + 1})")
            prices = await get_crypto_prices()
            logger.info("Successfully fetched prices")
            return prices
            
        except APITimeoutError as e:
            last_error = e
            logger.warning(f"Price fetch timeout (attempt {retry_count + 1}): {e}")
            
        except APIRateLimitError as e:
            last_error = e
            logger.warning(f"Rate limited (attempt {retry_count + 1}): {e}")
            
        except APIError as e:
            last_error = e
            logger.error(f"API error fetching prices (attempt {retry_count + 1}): {e}")
            
        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error fetching prices (attempt {retry_count + 1}): {e}")
        
        retry_count += 1
        if retry_count <= max_retries:
            # Exponential backoff for retries
            delay = settings.api_retry_delay * (2 ** retry_count)
            logger.info(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
    
    logger.error(f"Failed to fetch prices after {max_retries + 1} attempts. Last error: {last_error}")
    return None


async def check_alerts_against_prices(
    active_alerts: List, 
    prices: Dict
) -> List[Dict]:
    """
    Check if any alerts have been triggered based on current prices.
    
    Args:
        active_alerts: List of active Alert objects from database
        prices: Dictionary with current prices (btc, eth, usdt, currency, timestamp)
        
    Returns:
        List of dictionaries with triggered alert info
    """
    triggered_alerts = []
    
    for alert in active_alerts:
        try:
            asset_lower = alert.asset.lower()
            
            # Get current price for this asset
            if asset_lower not in prices:
                logger.warning(f"Price data missing for asset {alert.asset}")
                continue
            
            current_price = prices[asset_lower]
            threshold = alert.threshold
            
            # Check if alert is triggered
            is_triggered = False
            
            if alert.direction == AlertDirection.ABOVE:
                is_triggered = current_price >= threshold
                direction_text = "≥"
            else:  # AlertDirection.BELOW
                is_triggered = current_price <= threshold
                direction_text = "≤"
            
            if is_triggered:
                logger.info(
                    f"Alert {alert.alert_id} TRIGGERED: "
                    f"{alert.asset} {current_price:.2f} {direction_text} {threshold:.2f}"
                )
                
                triggered_alerts.append({
                    'alert': alert,
                    'current_price': current_price,
                    'threshold': threshold,
                    'direction': alert.direction,
                    'asset': alert.asset,
                    'user_id': alert.user_id,
                    'asset_lower': asset_lower,
                })
            else:
                logger.debug(
                    f"Alert {alert.alert_id} not triggered: "
                    f"{alert.asset} {current_price:.2f} vs {threshold:.2f}"
                )
        
        except Exception as e:
            logger.error(
                f"Error checking alert {alert.alert_id}: {e}",
                exc_info=True
            )
            continue
    
    return triggered_alerts


async def send_alert_notifications(bot: Bot, triggered_alerts: List[Dict]) -> None:
    """
    Send Telegram notifications for triggered alerts.
    
    Args:
        bot: Aiogram Bot instance
        triggered_alerts: List of triggered alert info dictionaries
    """
    for alert_info in triggered_alerts:
        try:
            user_id = alert_info['user_id']
            alert = alert_info['alert']
            
            # Get user's language preference
            user_language = alert.language_preference or "en"
            
            # Build notification message
            direction_text = "above" if alert_info['direction'] == AlertDirection.ABOVE else "below"
            
            # Get localized direction text
            try:
                direction_label = localization.get_text(f"alerts.{direction_text}", user_language)
            except Exception:
                direction_label = direction_text
            
            # Format the message
            message_text = (
                f"🚨 <b>Price Alert Triggered!</b>\n\n"
                f"<b>Asset:</b> {alert_info['asset'].upper()}\n"
                f"<b>Current Price:</b> ₽{alert_info['current_price']:,.2f}\n"
                f"<b>Alert Threshold:</b> ₽{alert_info['threshold']:,.2f}\n"
                f"<b>Condition:</b> {direction_label}\n"
                f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            
            # Send message with retry logic
            success = await send_message_with_retry(
                bot=bot,
                chat_id=user_id,
                text=message_text,
                max_retries=3
            )
            
            if success:
                logger.info(f"Sent alert notification to user {user_id} for alert {alert.alert_id}")
                
                # Update alert status to TRIGGERED
                status_updated = await AlertRepository.update_alert_status(
                    alert.alert_id,
                    AlertStatus.TRIGGERED
                )
                
                if status_updated:
                    logger.info(f"Updated alert {alert.alert_id} status to TRIGGERED")
                else:
                    logger.warning(f"Failed to update alert {alert.alert_id} status")
            else:
                logger.warning(f"Failed to send notification to user {user_id} after retries")
        
        except Exception as e:
            logger.error(
                f"Error sending notification for alert {alert_info.get('alert', {}).alert_id}: {e}",
                exc_info=True
            )
            continue


async def send_message_with_retry(
    bot: Bot,
    chat_id: int,
    text: str,
    max_retries: int = 3
) -> bool:
    """
    Send a Telegram message with retry logic.
    
    Args:
        bot: Aiogram Bot instance
        chat_id: Telegram chat ID
        text: Message text
        max_retries: Maximum number of retries
        
    Returns:
        True if message sent successfully, False otherwise
    """
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            logger.debug(f"Sending message to chat {chat_id} (attempt {retry_count + 1})")
            
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            
            logger.info(f"Successfully sent message to chat {chat_id}")
            return True
        
        except Exception as e:
            logger.warning(f"Error sending message (attempt {retry_count + 1}): {e}")
            retry_count += 1
            
            if retry_count <= max_retries:
                # Exponential backoff
                delay = 1.0 * (2 ** retry_count)
                logger.info(f"Retrying message send in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
    
    logger.error(f"Failed to send message to chat {chat_id} after {max_retries + 1} attempts")
    return False


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance."""
    return scheduler
