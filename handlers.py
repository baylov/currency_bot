from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from localization import localization
from database import User, get_db_session, AlertDirection, AlertStatus
from database_alerts import AlertRepository
from api_client import get_crypto_prices, APIError
from utils.logger import get_logger
from utils.localization_helpers import (
    send_localized_message,
    edit_localized_message,
    create_language_keyboard,
    handle_language_change,
    get_localized_text,
)

logger = get_logger(__name__)
router = Router()

# Constants for assets
SUPPORTED_ASSETS = {
    "btc": "Bitcoin",
    "eth": "Ethereum",
    "usdt": "Tether",
}

# Store temporary state for multi-step interactions
_user_state = {}


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
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=None
                )
                session.add(user)
                await session.commit()
                logger.info(f"Created new user: {telegram_id}")
                
    except Exception as e:
        logger.error(f"Error ensuring user exists: {e}")


async def get_user_display_language(telegram_id: str) -> str:
    """Get the display name of user's language preference."""
    user_lang = await localization.get_user_language(telegram_id)
    supported = localization.get_supported_languages()
    return supported.get(user_lang, "Unknown")


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    """Handle /start command."""
    await ensure_user_exists(
        telegram_id=str(message.from_user.id),
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    await send_localized_message(message, "commands.start")
    logger.info(f"User {message.from_user.id} started the bot")


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handle /help command."""
    await send_localized_message(message, "commands.help")
    logger.info(f"User {message.from_user.id} requested help")


@router.message(Command("status"))
async def handle_status(message: Message) -> None:
    """Handle /status command."""
    await send_localized_message(message, "commands.status")
    logger.info(f"User {message.from_user.id} checked status")


@router.message(Command("language"))
async def handle_language(message: Message) -> None:
    """Handle /language command."""
    keyboard = await create_language_keyboard()
    await send_localized_message(
        message, 
        "commands.language_select",
        reply_markup=keyboard
    )
    logger.info(f"User {message.from_user.id} opened language selection")


@router.message(Command("prices"))
async def handle_prices(message: Message) -> None:
    """Handle /prices command - fetch and display cryptocurrency prices."""
    try:
        status_msg = await message.answer("⏳ Fetching current prices...")
        
        prices = await get_crypto_prices()
        
        response = (
            f"💰 <b>Current Cryptocurrency Prices ({prices['currency']})</b>\n\n"
            f"₿ <b>Bitcoin:</b> {prices['btc']:,.2f} ₽\n"
            f"Ξ <b>Ethereum:</b> {prices['eth']:,.2f} ₽\n"
            f"₮ <b>Tether:</b> {prices['usdt']:.2f} ₽\n"
        )
        
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


@router.message(Command("setalert"))
async def handle_setalert(message: Message) -> None:
    """Handle /setalert command - start alert creation flow."""
    user_id = message.from_user.id
    telegram_id = str(user_id)
    
    try:
        # Create asset selection keyboard
        builder = InlineKeyboardBuilder()
        for asset_code, asset_name in SUPPORTED_ASSETS.items():
            builder.add(
                InlineKeyboardButton(
                    text=f"{asset_name} ({asset_code.upper()})",
                    callback_data=f"alert_asset_{asset_code}"
                )
            )
        builder.adjust(1)
        
        text = await get_localized_text(telegram_id, "alerts.select_asset")
        await message.answer(text, reply_markup=builder.as_markup())
        
        logger.info(f"User {user_id} started alert creation")
        
    except Exception as e:
        logger.error(f"Error in setalert handler: {e}", exc_info=True)
        await send_localized_message(message, "errors.general")


@router.message(Command("myalerts"))
async def handle_myalerts(message: Message) -> None:
    """Handle /myalerts command - show user's alerts."""
    user_id = message.from_user.id
    telegram_id = str(user_id)
    
    try:
        alerts = await AlertRepository.list_alerts_by_user(user_id, AlertStatus.ACTIVE)
        
        if not alerts:
            text = await get_localized_text(telegram_id, "alerts.no_alerts")
            await message.answer(text)
            logger.info(f"User {user_id} has no active alerts")
            return
        
        # Build alerts list
        header = await get_localized_text(telegram_id, "alerts.alert_list_header")
        alert_lines = []
        
        for alert in alerts:
            direction_text = await get_localized_text(
                telegram_id, 
                f"alerts.{alert.direction.value}"
            )
            
            alert_text = await get_localized_text(
                telegram_id,
                "alerts.alert_item",
                asset=alert.asset.upper(),
                direction=direction_text,
                threshold=alert.threshold,
                alert_id=alert.alert_id[:8]
            )
            alert_lines.append(alert_text)
        
        response = header + "\n".join(alert_lines)
        await message.answer(response)
        
        logger.info(f"User {user_id} viewed {len(alerts)} alerts")
        
    except Exception as e:
        logger.error(f"Error in myalerts handler: {e}", exc_info=True)
        await send_localized_message(message, "errors.general")


@router.message(Command("remove"))
async def handle_remove(message: Message) -> None:
    """Handle /remove command - start alert removal flow."""
    user_id = message.from_user.id
    telegram_id = str(user_id)
    
    try:
        alerts = await AlertRepository.list_alerts_by_user(user_id, AlertStatus.ACTIVE)
        
        if not alerts:
            text = await get_localized_text(telegram_id, "alerts.no_alerts")
            await message.answer(text)
            return
        
        # Create keyboard with alerts to remove
        builder = InlineKeyboardBuilder()
        for alert in alerts:
            direction_text = await get_localized_text(
                telegram_id,
                f"alerts.{alert.direction.value}"
            )
            
            button_text = f"{alert.asset.upper()} {direction_text} ₽{alert.threshold:.2f}"
            builder.add(
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"remove_alert_{alert.alert_id}"
                )
            )
        
        builder.adjust(1)
        
        header = await get_localized_text(telegram_id, "alerts.alert_list_header")
        await message.answer(header + "Select an alert to remove:", reply_markup=builder.as_markup())
        
        logger.info(f"User {user_id} started alert removal")
        
    except Exception as e:
        logger.error(f"Error in remove handler: {e}", exc_info=True)
        await send_localized_message(message, "errors.general")


@router.message(Command("settings"))
async def handle_settings(message: Message) -> None:
    """Handle /settings command - show settings with language toggle."""
    user_id = message.from_user.id
    telegram_id = str(user_id)
    
    try:
        current_language = await get_user_display_language(telegram_id)
        
        # Get language keyboard
        keyboard = await create_language_keyboard()
        
        text = await get_localized_text(
            telegram_id,
            "commands.settings",
            current_language=current_language
        )
        
        await message.answer(text, reply_markup=keyboard)
        
        logger.info(f"User {user_id} opened settings")
        
    except Exception as e:
        logger.error(f"Error in settings handler: {e}", exc_info=True)
        await send_localized_message(message, "errors.general")


@router.callback_query(F.data.startswith("lang_"))
async def handle_language_selection(callback: CallbackQuery) -> None:
    """Handle language selection callback."""
    user_id = callback.from_user.id
    
    success = await handle_language_change(callback)
    if success:
        logger.info(f"User {user_id} changed language via settings")
    else:
        logger.warning(f"Language change failed for user {user_id}")


@router.callback_query(F.data.startswith("alert_asset_"))
async def handle_alert_asset_selection(callback: CallbackQuery) -> None:
    """Handle asset selection for alert creation."""
    user_id = callback.from_user.id
    telegram_id = str(user_id)
    
    try:
        asset = callback.data.split("_")[2]
        
        if asset not in SUPPORTED_ASSETS:
            await callback.answer("Invalid asset selected")
            logger.warning(f"User {user_id} selected invalid asset: {asset}")
            return
        
        # Store asset in user state
        _user_state[user_id] = {"asset": asset}
        
        # Show direction selection
        builder = InlineKeyboardBuilder()
        
        above_text = await get_localized_text(telegram_id, "keyboard.above")
        below_text = await get_localized_text(telegram_id, "keyboard.below")
        
        builder.add(
            InlineKeyboardButton(text=above_text, callback_data=f"alert_dir_above_{asset}"),
            InlineKeyboardButton(text=below_text, callback_data=f"alert_dir_below_{asset}")
        )
        builder.adjust(2)
        
        asset_display = SUPPORTED_ASSETS[asset]
        direction_prompt = await get_localized_text(
            telegram_id,
            "alerts.select_direction",
            asset=asset_display
        )
        
        await edit_localized_message(callback, "alerts.select_direction", reply_markup=builder.as_markup(), asset=asset_display)
        await callback.answer()
        
        logger.info(f"User {user_id} selected asset {asset} for alert")
        
    except Exception as e:
        logger.error(f"Error in alert asset selection: {e}", exc_info=True)
        await callback.answer("Error processing your selection")


@router.callback_query(F.data.startswith("alert_dir_"))
async def handle_alert_direction_selection(callback: CallbackQuery) -> None:
    """Handle direction selection for alert creation."""
    user_id = callback.from_user.id
    telegram_id = str(user_id)
    
    try:
        parts = callback.data.split("_")
        direction = parts[2]
        asset = parts[3]
        
        if direction not in ["above", "below"]:
            await callback.answer("Invalid direction selected")
            logger.warning(f"User {user_id} selected invalid direction: {direction}")
            return
        
        # Store direction in user state
        if user_id in _user_state:
            _user_state[user_id]["direction"] = direction
        else:
            _user_state[user_id] = {"asset": asset, "direction": direction}
        
        # Ask for price
        asset_display = SUPPORTED_ASSETS[asset]
        price_prompt = await get_localized_text(
            telegram_id,
            "alerts.enter_price",
            asset=asset_display
        )
        
        await callback.message.answer(price_prompt)
        await callback.answer()
        
        logger.info(f"User {user_id} selected direction {direction} for asset {asset}")
        
    except Exception as e:
        logger.error(f"Error in alert direction selection: {e}", exc_info=True)
        await callback.answer("Error processing your selection")


@router.message()
async def handle_message_in_alert_flow(message: Message) -> None:
    """Handle text messages for price input in alert flow."""
    user_id = message.from_user.id
    telegram_id = str(user_id)
    
    # Check if user is in alert creation flow
    if user_id not in _user_state:
        await handle_unknown_message(message)
        return
    
    state = _user_state[user_id]
    if "direction" not in state or "asset" not in state:
        await handle_unknown_message(message)
        return
    
    try:
        # Parse price
        price_text = message.text.strip()
        
        try:
            threshold = float(price_text)
            if threshold <= 0:
                raise ValueError("Price must be positive")
        except (ValueError, TypeError):
            error_msg = await get_localized_text(telegram_id, "errors.invalid_price")
            await message.answer(error_msg)
            logger.warning(f"User {user_id} entered invalid price: {price_text}")
            return
        
        # Create alert
        asset = state["asset"]
        direction_str = state["direction"]
        direction = AlertDirection.ABOVE if direction_str == "above" else AlertDirection.BELOW
        user_language = await localization.get_user_language(telegram_id)
        
        alert = await AlertRepository.create_alert(
            user_id=user_id,
            asset=asset,
            threshold=threshold,
            direction=direction,
            language_preference=user_language
        )
        
        if alert:
            direction_text = await get_localized_text(telegram_id, f"alerts.{direction_str}")
            
            confirmation = await get_localized_text(
                telegram_id,
                "alerts.alert_created",
                asset=asset.upper(),
                direction=direction_text,
                threshold=threshold
            )
            
            await message.answer(confirmation)
            logger.info(f"Alert created for user {user_id}: {asset} {direction_str} {threshold}")
        else:
            await send_localized_message(message, "errors.general")
            logger.error(f"Failed to create alert for user {user_id}")
        
        # Clean up state
        del _user_state[user_id]
        
    except Exception as e:
        logger.error(f"Error processing alert price input: {e}", exc_info=True)
        await send_localized_message(message, "errors.general")


@router.callback_query(F.data.startswith("remove_alert_"))
async def handle_remove_alert(callback: CallbackQuery) -> None:
    """Handle alert removal confirmation."""
    user_id = callback.from_user.id
    telegram_id = str(user_id)
    
    try:
        alert_id = callback.data.replace("remove_alert_", "")
        
        # Verify alert belongs to user
        alert = await AlertRepository.get_alert_by_id(alert_id)
        if not alert or alert.user_id != user_id:
            await callback.answer("Alert not found or doesn't belong to you")
            logger.warning(f"User {user_id} tried to remove alert {alert_id} that doesn't exist or isn't theirs")
            return
        
        # Delete alert
        success = await AlertRepository.delete_alert(alert_id)
        
        if success:
            removed_msg = await get_localized_text(telegram_id, "alerts.alert_removed")
            await callback.message.answer(removed_msg)
            logger.info(f"User {user_id} removed alert {alert_id}")
        else:
            await callback.message.answer("Failed to remove alert. Please try again.")
            logger.error(f"Failed to delete alert {alert_id} for user {user_id}")
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in remove alert handler: {e}", exc_info=True)
        await callback.answer("Error processing your request")


@router.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages."""
    await send_localized_message(message, "commands.unknown")
    logger.debug(f"User {message.from_user.id} sent unknown message: {message.text}")
