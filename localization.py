import json
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.logger import get_logger
from database import User, get_db_session

logger = get_logger(__name__)


class LocalizationManager:
    """Manager for handling localization and translations with user preference persistence."""
    
    def __init__(self, locale_dir: str = "locales"):
        self.locale_dir = Path(locale_dir)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "en"
        self.supported_languages = ["en", "ru"]
        # In-memory cache for user language preferences
        self._user_language_cache: Dict[str, str] = {}
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load all translation files."""
        try:
            if not self.locale_dir.exists():
                self.locale_dir.mkdir(exist_ok=True)
                logger.warning(f"Locale directory created at {self.locale_dir}")
                return
            
            for locale_file in self.locale_dir.glob("*.json"):
                language_code = locale_file.stem
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[language_code] = json.load(f)
                logger.info(f"Loaded translations for {language_code}")
        
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
    
    async def get_user_language(self, telegram_id: str) -> str:
        """Get user's preferred language from cache or database."""
        # Check cache first
        if telegram_id in self._user_language_cache:
            return self._user_language_cache[telegram_id]
        
        # Fallback to database
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(User.language_code).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if user and user.language_code:
                    language = user.language_code
                else:
                    # Use Telegram's language code if available, otherwise default
                    language = self.default_language
                
                # Cache the result
                self._user_language_cache[telegram_id] = language
                return language
                
        except Exception as e:
            logger.error(f"Error fetching user language: {e}")
            return self.default_language
    
    async def set_user_language(self, telegram_id: str, language: str) -> bool:
        """Set user's preferred language in database and cache."""
        if language not in self.supported_languages:
            logger.warning(f"Unsupported language '{language}' for user {telegram_id}")
            return False
        
        try:
            async with get_db_session() as session:
                # Update or create user record
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    user.language_code = language
                else:
                    # Create new user record if doesn't exist
                    user = User(telegram_id=telegram_id, language_code=language)
                    session.add(user)
                
                await session.commit()
                
                # Update cache
                self._user_language_cache[telegram_id] = language
                logger.info(f"Set language '{language}' for user {telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting user language: {e}")
            return False
    
    def get_text(
        self, 
        key: str, 
        language: Optional[str] = None,
        **kwargs
    ) -> str:
        """Get localized text by key."""
        lang = language or self.default_language
        
        # Handle nested keys (e.g., "commands.start")
        keys = key.split('.')
        text = None
        
        # Try to get translation for the specified language
        if lang in self.translations:
            text = self._get_nested_value(self.translations[lang], keys)
        
        # Fallback to default language if not found
        if text is None and lang != self.default_language and self.default_language in self.translations:
            text = self._get_nested_value(self.translations[self.default_language], keys)
        
        # Fallback to key itself if still not found
        if text is None:
            text = key
            logger.warning(f"Translation key '{key}' not found for language '{lang}'")
        
        # Format with kwargs if provided
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, ValueError) as e:
            logger.error(f"Error formatting translation '{key}': {e}")
            return text
    
    def _get_nested_value(self, data: Dict[str, Any], keys: list) -> Optional[str]:
        """Get nested value from dictionary using key path."""
        current = data
        try:
            for key in keys:
                current = current[key]
            return current if isinstance(current, str) else str(current)
        except (KeyError, TypeError):
            return None
    
    async def get_user_text(
        self, 
        telegram_id: str, 
        key: str, 
        **kwargs
    ) -> str:
        """Get localized text for a specific user based on their preference."""
        user_language = await self.get_user_language(telegram_id)
        return self.get_text(key, user_language, **kwargs)
    
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """Short alias for get_text."""
        return self.get_text(key, language, **kwargs)
    
    async def ut(self, telegram_id: str, key: str, **kwargs) -> str:
        """Short alias for get_user_text."""
        return await self.get_user_text(telegram_id, key, **kwargs)
    
    def get_keyboard_label(self, key: str, language: Optional[str] = None) -> str:
        """Get localized keyboard button label."""
        # Keyboard labels are typically shorter, so we look for them in a specific section
        keyboard_key = f"keyboard.{key}"
        return self.get_text(keyboard_key, language) or self.get_text(key, language)
    
    async def get_user_keyboard_label(self, telegram_id: str, key: str) -> str:
        """Get localized keyboard button label for a specific user."""
        user_language = await self.get_user_language(telegram_id)
        return self.get_keyboard_label(key, user_language)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages with their display names."""
        return {
            "en": "English",
            "ru": "Русский"
        }
    
    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported."""
        return language in self.supported_languages


# Global localization manager instance
localization = LocalizationManager()