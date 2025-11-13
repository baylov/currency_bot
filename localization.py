import json
from typing import Dict, Any, Optional
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class LocalizationManager:
    """Manager for handling localization and translations."""
    
    def __init__(self, locale_dir: str = "locales"):
        self.locale_dir = Path(locale_dir)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "en"
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
    
    def get_text(
        self, 
        key: str, 
        language: Optional[str] = None,
        **kwargs
    ) -> str:
        """Get localized text by key."""
        lang = language or self.default_language
        
        # Try to get translation for the specified language
        if lang in self.translations and key in self.translations[lang]:
            text = self.translations[lang][key]
        # Fallback to default language
        elif self.default_language in self.translations and key in self.translations[self.default_language]:
            text = self.translations[self.default_language][key]
        # Fallback to key itself
        else:
            text = key
            logger.warning(f"Translation key '{key}' not found for language '{lang}'")
        
        # Format with kwargs if provided
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, ValueError) as e:
            logger.error(f"Error formatting translation '{key}': {e}")
            return text
    
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """Short alias for get_text."""
        return self.get_text(key, language, **kwargs)


# Global localization manager instance
localization = LocalizationManager()