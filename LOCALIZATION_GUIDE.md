# Localization System Guide

This guide explains how to use the localization system implemented for the Telegram bot.

## Overview

The localization system provides:
- Multi-language support for Russian and English
- User language preference persistence via SQLite
- In-memory caching with database fallback
- Helper functions for handlers
- Structured translation dictionaries

## Architecture

### Core Components

1. **LocalizationManager** (`localization.py`)
   - Main class managing translations and user preferences
   - Handles caching, database operations, and text retrieval

2. **Translation Files** (`locales/`)
   - `en.json` - English translations
   - `ru.json` - Russian translations
   - Structured with nested keys (commands, errors, messages, keyboard)

3. **Database Integration**
   - User language preferences stored in `users.language_code`
   - In-memory cache for performance
   - Automatic fallback to database

4. **Helper Functions** (`utils/localization_helpers.py`)
   - Utility functions for handlers
   - Simplified API for common operations

## Usage

### Basic Text Retrieval

```python
from localization import localization

# Get text in specific language
text = localization.get_text("commands.start", "en")

# Get text in default language
text = localization.get_text("commands.start")

# Use short alias
text = localization.t("commands.start", "en")
```

### User-Specific Text

```python
# Get text based on user's preference
user_text = await localization.get_user_text(user_id, "commands.start")

# Use short alias
user_text = await localization.ut(user_id, "commands.start")
```

### Language Management

```python
# Set user language preference
success = await localization.set_user_language(user_id, "ru")

# Get user's current language
user_lang = await localization.get_user_language(user_id)

# Check if language is supported
is_supported = localization.is_language_supported("ru")

# Get all supported languages
languages = localization.get_supported_languages()
```

### Handler Integration

```python
from utils.localization_helpers import (
    send_localized_message,
    create_language_keyboard,
    handle_language_change
)

# Send localized message
await send_localized_message(message, "commands.start")

# Create language selection keyboard
keyboard = await create_language_keyboard()
await send_localized_message(message, "commands.language_select", reply_markup=keyboard)

# Handle language change callback
await handle_language_change(callback)
```

## Translation Structure

Translation files use nested JSON structure:

```json
{
  "commands": {
    "start": "Welcome message...",
    "help": "Help text...",
    "status": "Status message..."
  },
  "errors": {
    "general": "General error...",
    "network": "Network error..."
  },
  "messages": {
    "bot_started": "Bot started!",
    "bot_stopped": "Bot stopped."
  },
  "keyboard": {
    "english": "English",
    "russian": "Русский",
    "back": "Back",
    "cancel": "Cancel"
  }
}
```

### Key Naming Conventions

- Use dot notation for nested keys: `"commands.start"`
- Group related translations: `"errors.general"`, `"errors.network"`
- Use descriptive, lowercase names with underscores
- Keyboard labels go under `"keyboard.*"` section

## Adding New Languages

1. Create new translation file: `locales/{lang_code}.json`
2. Copy structure from existing files
3. Translate all strings
4. Add language to `LocalizationManager.supported_languages`
5. Add to `get_supported_languages()` method

Example for adding German:

```python
# In localization.py
self.supported_languages = ["en", "ru", "de"]

def get_supported_languages(self) -> Dict[str, str]:
    return {
        "en": "English",
        "ru": "Русский",
        "de": "Deutsch"
    }
```

## Adding New Translations

1. Add keys to all translation files
2. Use consistent structure across languages
3. Test with both languages
4. Update handlers to use new keys

## Features

### Caching System

- In-memory cache for user language preferences
- Automatic cache updates when language changes
- Database fallback for cache misses
- Performance optimization for frequent requests

### Fallback Mechanism

- User's preferred language → Default language → Key name
- Graceful degradation when translations are missing
- Warning logs for missing keys
- Never crashes due to missing translations

### Formatting Support

```python
# Translation with placeholders
text = "Hello {name}, you have {count} messages!"

# Use with kwargs
formatted = await localization.ut(user_id, "greeting", name="John", count=5)
# Result: "Hello John, you have 5 messages!"
```

### Keyboard Localization

```python
# Get localized keyboard label
button_text = await localization.get_user_keyboard_label(user_id, "back")
# Returns "Back" for English users, "Назад" for Russian users
```

## Best Practices

1. **Always use localization** - Never hardcode text in handlers
2. **Use descriptive keys** - Make keys self-documenting
3. **Test both languages** - Ensure all translations work
4. **Handle missing keys gracefully** - System provides fallbacks
5. **Use helper functions** - Simplify handler code
6. **Keep translations consistent** - Same tone and terminology
7. **Document complex keys** - Add comments for unclear translations

## Commands

The system adds a `/language` command that:
- Shows language selection keyboard
- Updates user preference
- Provides confirmation in selected language

## Database Schema

The `users` table includes:
- `telegram_id` - User's Telegram ID
- `language_code` - User's preferred language (nullable)
- Other user information fields

## Error Handling

- Missing translations log warnings but don't crash
- Database errors fall back to default language
- Invalid language codes are rejected with warnings
- Cache failures fall back to database queries

## Performance

- In-memory cache reduces database queries
- Lazy loading of translation files
- Efficient nested key lookup
- Minimal overhead for text retrieval

## Testing

Test the localization system by:

1. Testing text retrieval in both languages
2. Verifying user language persistence
3. Checking fallback mechanisms
4. Testing keyboard localization
5. Verifying cache functionality

The system has been thoroughly tested and handles edge cases gracefully.