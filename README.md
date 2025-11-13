# Async Telegram Crypto Alert Bot

An asynchronous Telegram bot template that provides localized cryptocurrency price alerts, scheduled notifications, and rich command handling. The project is built on top of [`aiogram` v3](https://docs.aiogram.dev/), [`APScheduler`](https://apscheduler.readthedocs.io/), and async SQLAlchemy, and ships with a resilient HTTP client for CoinGecko price data.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Bot](#running-the-bot)
- [Scheduler Behaviour](#scheduler-behaviour)
- [Logging](#logging)
- [Localization](#localization)
- [Alert Functionality](#alert-functionality)
- [Functional Telegram Testing](#functional-telegram-testing)
- [Development Commands](#development-commands)
- [License](#license)

## Overview
This bot delivers near real-time cryptocurrency alerts directly to Telegram users. Key capabilities include:

- Async/await foundation with aiogram v3 and aiohttp
- Persistent user onboarding and multi-language support (English/Russian)
- CoinGecko-backed price fetching with retry-aware API client
- Alert creation, listing, and removal stored in an async SQL database
- Background scheduler that evaluates alerts every five minutes
- Structured logging with configurable verbosity

The repository is organised as follows:

```
.
├── main.py              # Application entry point
├── handlers.py          # Telegram command and callback handlers
├── scheduler.py         # APScheduler job configuration
├── api_client.py        # CoinGecko client with retry logic
├── database.py          # SQLAlchemy models and engine
├── database_alerts.py   # Alert repository helpers
├── localization.py      # Localization manager and helpers
├── locales/             # en.json and ru.json translation catalogs
├── utils/logger.py      # Logging configuration helpers
├── requirements.txt     # Runtime dependencies
├── pyproject.toml       # Project metadata
└── .env.example         # Sample environment configuration
```

## Prerequisites
Before you begin, ensure you have the following:

- **Python** 3.9 or later (the project targets 3.9+ in `pyproject.toml`)
- **pip** for dependency management
- **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- **Database** reachable via an async SQLAlchemy URL
  - Production: PostgreSQL (e.g. `postgresql+asyncpg://user:pass@host:5432/dbname`)
  - Local testing: SQLite is supported via `sqlite+aiosqlite:///./alerts.db`
- Optional: A virtual environment manager such as `venv` or `pyenv`

## Installation
1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd async-telegram-bot
   ```

2. **Create and activate a virtual environment** (recommended)
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # or install in editable mode with extras
   pip install -e .
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Update `.env` with the values that match your infrastructure (see the next section for details).

## Environment Configuration
The bot uses [`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to load configuration from the `.env` file. The provided [.env.example](./.env.example) enumerates all supported variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from BotFather. |
| `DATABASE_URL` | ✅ | Async SQLAlchemy URL (`postgresql+asyncpg://…` or `sqlite+aiosqlite:///…`). |
| `COINGECKO_BASE_URL` | ❌ | CoinGecko API base URL (default: `https://api.coingecko.com/api/v3`). |
| `API_TIMEOUT` | ❌ | Timeout (seconds) for API requests (default: `30`). |
| `API_MAX_RETRIES` | ❌ | Max retry attempts for price fetches (default: `3`). |
| `API_RETRY_DELAY` | ❌ | Base delay (seconds) used for exponential backoff (default: `1.0`). |
| `SCHEDULER_TIMEZONE` | ❌ | Timezone used by APScheduler (default: `UTC`). |
| `SCHEDULER_MAX_WORKERS` | ❌ | Max worker threads for APScheduler (default: `3`). |
| `PROXY_URL` / `PROXY_USERNAME` / `PROXY_PASSWORD` | ❌ | Optional HTTP proxy credentials. |
| `LOG_LEVEL` | ❌ | Application log level (`INFO`, `DEBUG`, etc.; default: `INFO`). |

> **Tip:** When targeting PostgreSQL, ensure the referenced database exists and is reachable. For SQLite, point `DATABASE_URL` to `sqlite+aiosqlite:///./alerts.db` (the tables will be created on first run).

## Database Setup
No manual migrations are required for local development. The `init_db()` routine in `main.py` automatically creates all tables when the bot starts. For production deployments, you may wish to manage schema migrations via Alembic (already listed in `pyproject.toml`).

## Running the Bot
With dependencies installed and `.env` configured, start the bot with:

```bash
python main.py
```

The main script performs the following steps automatically:
1. Configures structured logging (`utils.logger.setup_logging`).
2. Instantiates the aiogram bot and dispatcher.
3. Initializes the database and ensures tables exist.
4. Bootstraps APScheduler via `setup_scheduler`.
5. Begins polling the Telegram API for updates.

> **Production note:** For long-running deployments consider using a process supervisor (systemd, Docker, or similar) and configure auto-restart policies.

## Scheduler Behaviour
The scheduler (`scheduler.py`) registers a single recurring job named `price_alert_checker` that runs every **5 minutes**. Each cycle:

1. Fetches current BTC/ETH/USDT prices via the CoinGecko client with exponential backoff.
2. Retrieves all `ACTIVE` alerts from the database.
3. Compares current prices against stored thresholds (≥ for "above", ≤ for "below").
4. Sends localized Telegram notifications for triggered alerts and marks them as `TRIGGERED`.
5. Uses an `asyncio.Lock` to guarantee only one check runs at a time.

If price data cannot be fetched after the configured retries, the job logs the failure and waits for the next cycle. Triggered alerts remain stored (with `TRIGGERED` status) for auditability.

## Logging
Logging is centralised through `utils.logger.setup_logging()` and streams to stdout using the format `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`. Key characteristics:

- `LOG_LEVEL` controls overall verbosity (`INFO` by default; set to `DEBUG` for troubleshooting).
- aiogram logs are reduced to `WARNING` to avoid noise, while APScheduler logs run at `INFO`.
- SQLAlchemy engine logs are muted (`WARNING`) unless you enable `echo=True` in `database.py` for SQL traces.
- Scheduler activity, alert evaluation results, and API errors are all logged with clear context.

## Localization
Localization lives in `localization.py` with translation catalogs under `locales/` (English and Russian). Highlights:

- Users can switch languages via the `/language` command which presents an inline keyboard.
- Translations are looked up using dot-separated keys (e.g. `commands.start`, `alerts.alert_created`).
- User preferences are cached in memory and persisted in the `users` table for subsequent sessions.
- Helper functions (`localization.t`, `localization.ut`, etc.) simplify fetching localized strings in handlers and scheduler routines.

When adding new user-facing strings, update both `locales/en.json` and `locales/ru.json` to maintain parity.

## Alert Functionality
Alerts allow users to be notified when cryptocurrency prices cross a particular threshold:

- `/setalert` walks the user through asset selection (BTC, ETH, USDT), direction (above/below), and target price.
- Alerts are stored in the `alerts` table with status management handled by `database_alerts.AlertRepository`.
- `/myalerts` lists all active alerts along with their thresholds and directions.
- `/remove` provides inline buttons to delete individual alerts.
- `/settings` exposes quick access to language preferences and other configurable options.
- When a price condition is met, the scheduler sends a localized notification and transitions the alert to `TRIGGERED` to avoid duplicate messages.

## Functional Telegram Testing
Follow these steps to perform an end-to-end test of the bot in Telegram:

1. **Create a bot** via [@BotFather](https://t.me/BotFather) and record the generated token.
2. **Update `.env`** with the new `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, and any proxy settings if Telegram is blocked in your region.
3. **Start the bot locally** with `python main.py` (ensure your machine can reach api.telegram.org and api.coingecko.com).
4. **Initiate a chat** with your bot in Telegram:
   - Send `/start` to register the user and receive the welcome message.
   - Use `/help` to review available commands.
   - Run `/language` to toggle between English and Russian and confirm localized responses.
5. **Create a test alert** using `/setalert`:
   - Choose an asset (e.g. BTC) and direction (`below`).
   - Provide a threshold slightly above/below the current market price to trigger within the next scheduler cycle.
6. **Verify alert storage** with `/myalerts`; you should see the alert listed.
7. **Wait for the scheduler** (up to 5 minutes). Once the price condition is met, the bot sends a notification and the alert status changes to `TRIGGERED`.
8. **Inspect logs** in the terminal for scheduler activity, price fetch attempts, and delivery status. If needed, adjust `LOG_LEVEL=DEBUG` for deeper insight.
9. **Clean up** by removing alerts with `/remove` and stopping the process with `Ctrl+C` in the terminal.

Repeat the flow in both languages to validate localization and ensure alerts behave as expected under different language settings.

## Development Commands
Common developer-friendly commands:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format, lint, and type-check (optional during development)
black .
ruff check --fix .
mypy .
```

> Linting and type-checking are enforced by automated tooling in CI; run them locally if you want pre-flight validation.

## License
MIT
