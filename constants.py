# Application constants

# Bot information
BOT_NAME = "Async Telegram Bot"
BOT_VERSION = "0.1.0"
BOT_DESCRIPTION = "Template for async Telegram bot with APScheduler"

# Command list
AVAILABLE_COMMANDS = [
    "/start - Start the bot",
    "/help - Show available commands", 
    "/status - Check bot status",
]

# Message limits
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024

# Time formats
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

# API constants
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1

# Scheduler job IDs
DAILY_MESSAGE_JOB = "daily_message"
PERIODIC_MESSAGE_JOB = "periodic_message"

# Database
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20