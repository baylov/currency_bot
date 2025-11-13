from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select

from localization import localization
from database import User, get_db_session
from api_client import get_crypto_prices, APIError
from utils.logger import get_logger
from utils.localization_helpers import (
    send_localized_message,
    edit_localized_message,
    create_language_keyboard,
    handle_language_change,
)

logger = get_logger(__name__)
router = Router()


async def ensure_user_exists(telegram_id: str, username: str = None, 
                           first_name: str = None, last_name: str = None) -> None:
    """Ensure user exists in database."""
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user with their Telegram language code if available
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=None  # Will be set when user chooses language
                )
                session.add(user)
                await session.commit()
                logger.info(f"Created new user: {telegram_id}")
                
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}")


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    """Handle /start command."""
    # Ensure user exists in database
    await ensure_user_exists(
        telegram_id=str(message.from_user.id),
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Send localized start message
    await send_localized_message(message, "commands.start")


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    await send_localized_message(message, "commands.help")


@router.message(Command("status"))
async def handle_status(message: Message) -> None:
    """Handle /status command."""
    await send_localized_message(message, "commands.status")


@router.message(Command("language"))
async def handle_language(message: Message) -> None:
    """Handle /language command."""
    # Create language selection keyboard
    keyboard = await create_language_keyboard()
    
    # Send localized prompt with keyboard
    await send_localized_message(
        message, 
        "commands.language_select",
        reply_markup=keyboard
    )


@router.message(Command("prices"))
async def handle_prices(message: Message) -> None:
    """Handle /prices command - fetch and display cryptocurrency prices."""
    try:
        # Send "fetching" message
        status_msg = await message.answer("⏳ Fetching current prices...")
        
        # Fetch prices from CoinGecko
        prices = await get_crypto_prices()
        
        # Format the response
        response = (
            f"💰 <b>Current Cryptocurrency Prices ({prices['currency']})</b>\n\n"
            f"₿ <b>Bitcoin:</b> {prices['btc']:,.2f} ₽\n"
            f"Ξ <b>Ethereum:</b> {prices['eth']:,.2f} ₽\n"
            f"₮ <b>Tether:</b> {prices['usdt']:.2f} ₽\n"
        )
        
        # Delete status message and send result
        await status_msg.delete()
        await message.answer(response, parse_mode="HTML")
        
        logger.info(f"Prices sent to user {message.from_user.id}")
        
    except APIError as e:
        logger.error(f"API error in prices handler: {e}")
        await message.answer(
            "❌ Failed to fetch prices from CoinGecko. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error in prices handler: {e}", exc_info=True)
        await message.answer(
            "❌ An unexpected error occurred. Please try again later."
        )


@router.callback_query(F.data.startswith("lang_"))
async def handle_language_selection(callback: CallbackQuery) -> None:
    """Handle language selection callback."""
    await handle_language_change(callback)


@router.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages."""
    await send_localized_message(message, "commands.unknown")