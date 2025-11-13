"""
Localization helper utilities for handlers.
"""

from typing import Any, Dict, Optional
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from localization import localization


async def get_localized_text(telegram_id: str, key: str, **kwargs) -> str:
    """
    Get localized text for a user.
    
    Args:
        telegram_id: User's Telegram ID
        key: Translation key
        **kwargs: Formatting arguments
        
    Returns:
        Localized text string
    """
    return await localization.ut(telegram_id, key, **kwargs)


async def send_localized_message(
    message: Message, 
    key: str, 
    reply_markup: Optional[Any] = None,
    **kwargs
) -> None:
    """
    Send a localized message to user.
    
    Args:
        message: Aiogram message object
        key: Translation key
        reply_markup: Optional reply markup
        **kwargs: Formatting arguments
    """
    text = await get_localized_text(str(message.from_user.id), key, **kwargs)
    await message.answer(text, reply_markup=reply_markup)


async def edit_localized_message(
    callback: CallbackQuery,
    key: str,
    reply_markup: Optional[Any] = None,
    **kwargs
) -> None:
    """
    Edit a message with localized text.
    
    Args:
        callback: Aiogram callback query object
        key: Translation key
        reply_markup: Optional reply markup
        **kwargs: Formatting arguments
    """
    text = await get_localized_text(str(callback.from_user.id), key, **kwargs)
    await callback.message.edit_text(text, reply_markup=reply_markup)


async def create_language_keyboard() -> InlineKeyboardMarkup:
    """
    Create a language selection keyboard.
    
    Returns:
        InlineKeyboardMarkup with language options
    """
    builder = InlineKeyboardBuilder()
    supported_languages = localization.get_supported_languages()
    
    for lang_code, lang_name in supported_languages.items():
        builder.add(
            InlineKeyboardButton(
                text=lang_name,
                callback_data=f"lang_{lang_code}"
            )
        )
    
    builder.adjust(1)  # One button per row
    return builder.as_markup()


async def handle_language_change(callback: CallbackQuery) -> bool:
    """
    Handle language change callback.
    
    Args:
        callback: Aiogram callback query object
        
    Returns:
        True if successful, False otherwise
    """
    if not callback.data or not callback.data.startswith("lang_"):
        return False
    
    language_code = callback.data.split("_")[1]
    telegram_id = str(callback.from_user.id)
    
    success = await localization.set_user_language(telegram_id, language_code)
    
    if success:
        confirm_text = localization.get_text("commands.language_set", language_code)
        await callback.message.edit_text(confirm_text)
    else:
        error_text = await get_localized_text(telegram_id, "errors.general")
        await callback.message.edit_text(error_text)
    
    await callback.answer()
    return success


async def ensure_user_language(telegram_id: str, default_to_telegram: bool = True) -> str:
    """
    Ensure user has a language preference set.
    
    Args:
        telegram_id: User's Telegram ID
        default_to_telegram: Whether to use Telegram's language code as fallback
        
    Returns:
        Language code
    """
    return await localization.get_user_language(telegram_id)


def get_language_flag(language_code: str) -> str:
    """
    Get flag emoji for language code.
    
    Args:
        language_code: Language code (en, ru, etc.)
        
    Returns:
        Flag emoji
    """
    flags = {
        "en": "🇺🇸",
        "ru": "🇷🇺",
    }
    return flags.get(language_code, "🌐")


def format_language_choice(language_code: str, language_name: str) -> str:
    """
    Format language choice with flag.
    
    Args:
        language_code: Language code
        language_name: Language display name
        
    Returns:
        Formatted string with flag
    """
    flag = get_language_flag(language_code)
    return f"{flag} {language_name}"


async def get_user_language_info(telegram_id: str) -> Dict[str, str]:
    """
    Get comprehensive language information for a user.
    
    Args:
        telegram_id: User's Telegram ID
        
    Returns:
        Dictionary with language info
    """
    user_lang = await localization.get_user_language(telegram_id)
    supported = localization.get_supported_languages()
    
    return {
        "current_language": user_lang,
        "current_language_name": supported.get(user_lang, "Unknown"),
        "current_flag": get_language_flag(user_lang),
        "supported_languages": supported,
        "is_default": user_lang == localization.default_language
    }