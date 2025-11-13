from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, Enum as SQLEnum
from datetime import datetime
import uuid
import enum

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Database engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL logging
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(Base):
    """User model for storing Telegram user information."""
    
    __tablename__ = "users"
    
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_bot = Column(Boolean, default=False, nullable=False)
    language_code = Column(String, nullable=True)


class MessageLog(Base):
    """Model for logging messages."""
    
    __tablename__ = "message_logs"
    
    telegram_id = Column(String, nullable=False)
    message_text = Column(Text, nullable=False)
    message_type = Column(String, nullable=False)  # 'command', 'text', etc.
    is_bot_message = Column(Boolean, default=False, nullable=False)


class AlertDirection(str, enum.Enum):
    """Alert direction types."""
    ABOVE = "above"
    BELOW = "below"


class AlertStatus(str, enum.Enum):
    """Alert status types."""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    DELETED = "deleted"


class Alert(Base):
    """Model for price alerts."""
    
    __tablename__ = "alerts"
    
    alert_id = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    asset = Column(String, nullable=False)  # 'btc', 'eth', 'usdt'
    threshold = Column(Float, nullable=False)
    direction = Column(SQLEnum(AlertDirection), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    language_preference = Column(String, default="en", nullable=False)


async def init_db() -> None:
    """Initialize the database by creating all tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_db_session() -> AsyncSession:
    """Get a database session."""
    return AsyncSessionLocal()


async def close_db() -> None:
    """Close the database connection."""
    await engine.dispose()