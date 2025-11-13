# API Client Usage Guide

## Overview

The `api_client.py` module provides an async CoinGecko API client with robust error handling, configurable retry logic, and exponential backoff. It's designed to fetch cryptocurrency prices (BTC, ETH, USDT) in RUB through a clean interface suitable for use in bot handlers and scheduled tasks.

## Features

- **Async/Await**: Fully asynchronous using aiohttp
- **Retry Logic**: Configurable retries with exponential backoff
- **Error Handling**: Specific exceptions for timeouts, rate limits, and API errors
- **Logging**: Comprehensive logging for debugging and monitoring
- **Configuration-Driven**: All settings managed via environment variables
- **Clean Interface**: Simple methods returning normalized data structures

## Configuration

Add these environment variables to your `.env` file:

```env
# API Configuration
COINGECKO_BASE_URL=https://api.coingecko.com/api/v3
API_TIMEOUT=30
API_MAX_RETRIES=3
API_RETRY_DELAY=1.0
```

- `API_TIMEOUT`: Request timeout in seconds (default: 30)
- `API_MAX_RETRIES`: Maximum number of retry attempts (default: 3)
- `API_RETRY_DELAY`: Base delay between retries in seconds (default: 1.0)

The retry mechanism uses exponential backoff: `delay * 2^retry_count`
- First retry: 2 seconds
- Second retry: 4 seconds
- Third retry: 8 seconds

For rate limiting (HTTP 429), the delay is doubled.

## Usage Examples

### 1. Simple Usage with Convenience Function

The easiest way to get prices:

```python
from api_client import get_crypto_prices

async def my_handler():
    try:
        prices = await get_crypto_prices()
        print(f"BTC: {prices['btc']} RUB")
        print(f"ETH: {prices['eth']} RUB")
        print(f"USDT: {prices['usdt']} RUB")
    except Exception as e:
        print(f"Error fetching prices: {e}")
```

### 2. Using Context Manager

For more control and multiple requests:

```python
from api_client import CoinGeckoClient, APIError

async def my_handler():
    async with CoinGeckoClient() as client:
        try:
            # Check API status
            status = await client.ping()
            print(f"API Status: {status}")
            
            # Get RUB prices
            prices = await client.get_rub_prices()
            print(f"BTC: {prices['btc']} RUB")
            
        except APIError as e:
            print(f"API Error: {e}")
```

### 3. In Telegram Bot Handlers

```python
from aiogram import Router, types
from aiogram.filters import Command
from api_client import get_crypto_prices, APIError

router = Router()

@router.message(Command("prices"))
async def cmd_prices(message: types.Message):
    """Handler to show cryptocurrency prices."""
    try:
        await message.answer("Fetching current prices...")
        
        prices = await get_crypto_prices()
        
        response = (
            f"💰 Current Cryptocurrency Prices (RUB):\n\n"
            f"₿ BTC: {prices['btc']:,.2f} ₽\n"
            f"Ξ ETH: {prices['eth']:,.2f} ₽\n"
            f"₮ USDT: {prices['usdt']:.2f} ₽\n"
        )
        
        await message.answer(response)
        
    except APIError as e:
        await message.answer(f"❌ Failed to fetch prices: {e}")
    except Exception as e:
        await message.answer(f"❌ Unexpected error: {e}")
```

### 4. In Scheduler Jobs

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from api_client import get_crypto_prices, APIError
from utils.logger import get_logger

logger = get_logger(__name__)

async def send_daily_prices(bot: Bot, chat_id: int):
    """Scheduled job to send daily price updates."""
    try:
        logger.info("Fetching daily prices...")
        
        prices = await get_crypto_prices()
        
        message = (
            f"📊 Daily Price Update ({prices['currency']}):\n\n"
            f"₿ Bitcoin: {prices['btc']:,.2f} ₽\n"
            f"Ξ Ethereum: {prices['eth']:,.2f} ₽\n"
            f"₮ Tether: {prices['usdt']:.2f} ₽\n"
        )
        
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info("Daily prices sent successfully")
        
    except APIError as e:
        logger.error(f"Failed to fetch prices: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in daily prices job: {e}", exc_info=True)

# In scheduler.py
scheduler.add_job(
    send_daily_prices,
    trigger=CronTrigger(hour=9, minute=0),
    args=[bot, admin_chat_id],
    id="daily_prices",
    name="Daily price update",
)
```

### 5. Custom Price Queries

For other currencies or coins, use the generic method:

```python
from api_client import CoinGeckoClient

async def get_custom_prices():
    async with CoinGeckoClient() as client:
        # Get Bitcoin and Ethereum in USD and EUR
        prices = await client.get_simple_price(
            ids="bitcoin,ethereum",
            vs_currencies="usd,eur",
            include_24hr_change=True,
        )
        return prices
```

## Data Structure

The `get_rub_prices()` method returns a `PriceData` TypedDict:

```python
{
    'btc': 7980354.0,      # Bitcoin price in RUB
    'eth': 261016.0,       # Ethereum price in RUB
    'usdt': 80.64,         # Tether price in RUB
    'timestamp': 1763058651,  # Unix timestamp of last update
    'currency': 'RUB'      # Currency code
}
```

## Error Handling

The module defines specific exceptions for better error handling:

- `APIError`: Base exception for all API errors
- `APITimeoutError`: Request timed out after all retries
- `APIRateLimitError`: Rate limit exceeded after all retries

```python
from api_client import (
    get_crypto_prices,
    APIError,
    APITimeoutError,
    APIRateLimitError,
)

async def safe_get_prices():
    try:
        return await get_crypto_prices()
    except APITimeoutError:
        # Handle timeout specifically
        print("Request timed out")
    except APIRateLimitError:
        # Handle rate limiting specifically
        print("Rate limit exceeded")
    except APIError as e:
        # Handle other API errors
        print(f"API error: {e}")
```

## Logging

The client logs important events at different levels:

- **DEBUG**: Session start/close, successful requests
- **INFO**: Price fetches, retry attempts
- **WARNING**: Rate limiting
- **ERROR**: Request failures, timeouts

Example log output:
```
2025-11-13 18:30:56,398 - api_client - INFO - Fetching RUB prices for BTC, ETH, and USDT
2025-11-13 18:30:56,398 - api_client - INFO - Fetching prices for bitcoin,ethereum,tether in rub
2025-11-13 18:30:56,586 - api_client - INFO - Successfully fetched RUB prices: BTC=7980354.00, ETH=261016.00, USDT=80.64
```

## Best Practices

1. **Always use try-except**: Handle potential API errors gracefully
2. **Use context managers**: Ensures proper session cleanup
3. **Cache results**: For frequently accessed data, consider caching prices
4. **Monitor logs**: Watch for rate limiting and errors
5. **Set reasonable timeouts**: Adjust `API_TIMEOUT` based on your needs
6. **Handle user feedback**: Inform users when API requests fail

## Testing

A test script is provided to verify the implementation:

```bash
python test_api_client.py
```

This tests:
- Context manager usage
- Convenience function
- API ping endpoint
- RUB price fetching

## Advanced Usage

### Session Management

For long-running applications, manage the session lifecycle:

```python
from api_client import CoinGeckoClient

# Create client
client = CoinGeckoClient()
await client.start_session()

try:
    # Use client multiple times
    prices1 = await client.get_rub_prices()
    prices2 = await client.get_rub_prices()
finally:
    # Clean up
    await client.close_session()
```

### Custom Retry Configuration

Modify retry behavior via environment variables:

```env
# More aggressive retries for unreliable networks
API_MAX_RETRIES=5
API_RETRY_DELAY=2.0

# Faster retries for stable networks
API_MAX_RETRIES=2
API_RETRY_DELAY=0.5
```

## API Rate Limits

CoinGecko free API has rate limits:
- ~10-50 calls/minute depending on endpoint
- The client automatically handles HTTP 429 responses
- Uses longer backoff for rate limiting (2x normal delay)

If you frequently hit rate limits:
1. Increase `API_RETRY_DELAY`
2. Cache results to reduce API calls
3. Consider CoinGecko Pro for higher limits

## Troubleshooting

### Connection Issues
```
APITimeoutError: Request timed out after 4 attempts
```
- Check network connectivity
- Increase `API_TIMEOUT`
- Verify CoinGecko API is accessible

### Rate Limiting
```
APIRateLimitError: API rate limit exceeded
```
- Reduce request frequency
- Implement caching
- Increase `API_RETRY_DELAY`

### Invalid Prices
```
prices['btc'] returns 0.0
```
- Check API response format hasn't changed
- Verify coin IDs are correct
- Check logs for API errors
