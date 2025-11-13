# Alert Storage System Guide

This guide explains the alert storage system implemented using SQLite with SQLAlchemy AsyncIO.

## Overview

The alert storage system provides persistent storage for price alerts with the following features:

- **Database Persistence**: Uses SQLite via SQLAlchemy AsyncIO for async operations
- **Alert Management**: Create, read, update, and delete alerts
- **Status Tracking**: Track alert status (active, triggered, paused, deleted)
- **User Association**: Link alerts to telegram users by user ID
- **Language Support**: Store user language preference with each alert
- **Automatic Initialization**: Database tables are created automatically on startup

## Database Schema

### Alert Table

The `Alert` model stores price alerts with the following fields:

```python
Alert(
    id: int                          # Auto-incrementing primary key
    alert_id: str                    # Unique UUID for the alert
    user_id: int                     # Telegram user ID
    asset: str                       # Asset code ('btc', 'eth', 'usdt')
    threshold: float                 # Price threshold
    direction: AlertDirection        # 'above' or 'below'
    status: AlertStatus              # 'active', 'triggered', 'paused', 'deleted'
    language_preference: str         # User's language ('en', 'ru')
    created_at: datetime             # Timestamp when alert was created
    updated_at: datetime             # Timestamp when alert was last updated
)
```

### Enums

**AlertDirection**:
- `ABOVE` - Alert triggers when price goes above threshold
- `BELOW` - Alert triggers when price goes below threshold

**AlertStatus**:
- `ACTIVE` - Alert is active and monitoring
- `TRIGGERED` - Alert condition met, pending notification
- `PAUSED` - Alert temporarily paused
- `DELETED` - Alert marked as deleted

## CRUD Operations

The `AlertRepository` class provides all CRUD operations:

### Create Alert

```python
from database_alerts import AlertRepository
from database import AlertDirection

alert = await AlertRepository.create_alert(
    user_id=123456789,
    asset='btc',
    threshold=50000.0,
    direction=AlertDirection.ABOVE,
    language_preference='en'
)
```

### Read Alert

```python
# Get alert by ID
alert = await AlertRepository.get_alert_by_id(alert_id='550e8400-e29b-41d4-a716-446655440000')
```

### List Alerts

```python
# List all alerts for a user
alerts = await AlertRepository.list_alerts_by_user(user_id=123456789)

# List active alerts for a user
alerts = await AlertRepository.list_alerts_by_user(
    user_id=123456789,
    status=AlertStatus.ACTIVE
)

# List all active alerts across all users (for monitoring)
active_alerts = await AlertRepository.list_active_alerts()

# Get alerts for a specific asset
btc_alerts = await AlertRepository.get_alerts_by_asset('btc')
```

### Update Alert Status

```python
from database import AlertStatus

# Mark alert as triggered
updated = await AlertRepository.update_alert_status(
    alert_id='550e8400-e29b-41d4-a716-446655440000',
    new_status=AlertStatus.TRIGGERED
)
```

### Delete Alert

```python
# Delete specific alert
deleted = await AlertRepository.delete_alert(
    alert_id='550e8400-e29b-41d4-a716-446655440000'
)

# Delete all alerts for a user
deleted_count = await AlertRepository.delete_alerts_by_user(user_id=123456789)
```

### Query Operations

```python
# Count alerts for a user
count = await AlertRepository.count_alerts_by_user(user_id=123456789)
```

## Usage Examples

### In Handlers

```python
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database_alerts import AlertRepository
from database import AlertDirection

router = Router()

@router.message(Command("alert"))
async def create_price_alert(message: Message) -> None:
    """Create a new price alert."""
    try:
        # Parse command: /alert btc 50000 above
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer("Usage: /alert <asset> <threshold> <above|below>")
            return
        
        asset = parts[1]
        threshold = float(parts[2])
        direction = AlertDirection.ABOVE if parts[3] == 'above' else AlertDirection.BELOW
        
        alert = await AlertRepository.create_alert(
            user_id=message.from_user.id,
            asset=asset,
            threshold=threshold,
            direction=direction,
            language_preference='en'
        )
        
        if alert:
            await message.answer(f"✅ Alert created for {asset.upper()} {direction.value} {threshold}")
        else:
            await message.answer("❌ Failed to create alert")
            
    except ValueError:
        await message.answer("❌ Invalid threshold value")
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        await message.answer("❌ An error occurred")
```

### In Scheduler

```python
from scheduler import scheduler
from database_alerts import AlertRepository
from database import AlertStatus
from api_client import get_crypto_prices

async def check_price_alerts(bot: Bot) -> None:
    """Check all active alerts and notify users if thresholds are met."""
    try:
        # Get current prices
        prices = await get_crypto_prices()
        
        # Get all active alerts
        alerts = await AlertRepository.list_active_alerts()
        
        for alert in alerts:
            current_price = prices.get(alert.asset)
            if not current_price:
                continue
            
            # Check alert condition
            condition_met = False
            if alert.direction.value == 'above' and current_price >= alert.threshold:
                condition_met = True
            elif alert.direction.value == 'below' and current_price <= alert.threshold:
                condition_met = True
            
            if condition_met:
                # Send notification to user
                message = f"🔔 Price Alert!\n{alert.asset.upper()}: {current_price:,.2f} {alert.direction.value} {alert.threshold}"
                await bot.send_message(chat_id=alert.user_id, text=message)
                
                # Mark alert as triggered
                await AlertRepository.update_alert_status(alert.alert_id, AlertStatus.TRIGGERED)
                
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")

# Add to scheduler
scheduler.add_job(
    check_price_alerts,
    trigger=IntervalTrigger(minutes=5),
    args=[bot],
    id="check_alerts",
    name="Check Price Alerts",
    replace_existing=True,
)
```

## Database Initialization

The database is automatically initialized on startup via `init_db()` in `main.py`:

```python
# In main.py
await init_db()
logger.info("Database initialized successfully")
```

The `init_db()` function:
1. Creates an async connection to the database
2. Executes DDL to create all tables (User, MessageLog, Alert)
3. Logs success or error

## Error Handling

All repository methods include comprehensive error handling:

- **SQLAlchemy Errors**: Database-specific errors are caught and logged
- **Unexpected Errors**: Generic exceptions are caught and logged
- **Return Values**: Methods return `None`/`False`/`0` on error, never raise

Example:

```python
try:
    alert = await AlertRepository.create_alert(...)
    if alert:
        # Success
        logger.info(f"Alert created: {alert.alert_id}")
    else:
        # Database error occurred
        logger.error("Failed to create alert")
except Exception as e:
    # Unexpected error
    logger.error(f"Error: {e}")
```

## Performance Considerations

- **Indexing**: `alert_id` and `user_id` are indexed for fast lookups
- **Session Management**: Uses async context managers for proper resource cleanup
- **Batch Operations**: Use `delete_alerts_by_user()` for bulk deletion instead of individual deletes
- **Query Optimization**: Methods fetch only necessary data

## Best Practices

1. **Always use AlertRepository** instead of direct database queries
2. **Handle errors gracefully** - Never let database errors crash the bot
3. **Use appropriate enums** - Always use `AlertDirection` and `AlertStatus` enums
4. **Cache results** when possible to reduce database queries
5. **Log all operations** for debugging and monitoring
6. **Test migrations** before production deployment
7. **Regular backups** of SQLite database file

## Integration with Localization

The `language_preference` field in the Alert model integrates with the localization system:

```python
from localization import localization

# When sending alert notification
alert = await AlertRepository.get_alert_by_id(alert_id)
message_key = "alerts.triggered"
notification = await localization.t(message_key, alert.language_preference)
```

## Database File Location

The SQLite database file location is configured via `DATABASE_URL` environment variable:

```bash
# .env
DATABASE_URL=sqlite+aiosqlite:///./alerts.db
```

This creates an `alerts.db` file in the project root directory.

## Troubleshooting

### Issue: "Database tables not created"
- Ensure `init_db()` is called in `main.py`
- Check `DATABASE_URL` environment variable is set correctly
- Verify write permissions on database directory

### Issue: "Alert not found"
- Verify alert_id is correct
- Check if alert was deleted or marked as deleted
- Use `list_alerts_by_user()` to verify alert exists

### Issue: "Slow queries"
- Check database file size and consider cleanup of old alerts
- Ensure indexes are created properly
- Consider adding query caching layer

### Issue: "Connection errors"
- Verify database connection string is valid
- Check if database file is locked by another process
- Ensure sufficient disk space for database growth
