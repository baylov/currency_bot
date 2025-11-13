# Async Telegram Bot Template

A modern asynchronous Telegram bot template built with aiogram and APScheduler support.

## Features

- **Async/Await**: Built with asyncio for high performance
- **aiogram v3**: Modern Telegram bot framework
- **APScheduler**: Scheduled task support
- **SQLAlchemy**: Async database ORM
- **Pydantic**: Configuration management with validation
- **Localization**: Multi-language support
- **Logging**: Structured logging configuration
- **Type Hints**: Full type annotation support

## Project Structure

```
.
├── main.py              # Application entry point
├── handlers.py          # Telegram handlers
├── scheduler.py         # APScheduler configuration
├── api_client.py        # HTTP API client (CoinGecko example)
├── database.py          # Database models and connection
├── config.py            # Configuration management
├── localization.py      # Localization support
├── constants.py         # Application constants
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project configuration
├── .env.example        # Environment variables example
├── utils/
│   ├── __init__.py
│   ├── logger.py       # Logging utilities
│   └── helpers.py      # Helper functions
└── locales/
    ├── en.json         # English translations
    └── ru.json         # Russian translations
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   # or
   pip install -e .
   ```

3. Copy environment file:
   ```bash
   cp .env.example .env
   ```

4. Configure your `.env` file with your Telegram bot token and other settings

5. Set up the database (PostgreSQL recommended)

## Usage

Run the bot:
```bash
python main.py
```

## Configuration

The bot uses environment variables for configuration. See `.env.example` for available options:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
- `DATABASE_URL`: PostgreSQL connection string (required)
- `COINGECKO_BASE_URL`: CoinGecko API base URL
- `SCHEDULER_TIMEZONE`: Scheduler timezone (default: UTC)
- `SCHEDULER_MAX_WORKERS`: Maximum scheduler workers (default: 3)
- `LOG_LEVEL`: Logging level (default: INFO)

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Code formatting:
```bash
black .
ruff check --fix .
mypy .
```

## License

MIT