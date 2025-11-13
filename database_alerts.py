"""Database CRUD operations for alerts."""

import uuid
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from database import Alert, AlertDirection, AlertStatus, get_db_session
from utils.logger import get_logger

logger = get_logger(__name__)


class AlertRepository:
    """Repository for managing alerts in the database."""
    
    @staticmethod
    async def create_alert(
        user_id: int,
        asset: str,
        threshold: float,
        direction: AlertDirection,
        language_preference: str = "en"
    ) -> Optional[Alert]:
        """Create a new alert for a user.
        
        Args:
            user_id: Telegram user ID (integer)
            asset: Asset code ('btc', 'eth', 'usdt')
            threshold: Price threshold
            direction: AlertDirection.ABOVE or AlertDirection.BELOW
            language_preference: User's language preference
            
        Returns:
            Created Alert object or None if failed
        """
        try:
            alert_id = str(uuid.uuid4())
            
            alert = Alert(
                alert_id=alert_id,
                user_id=user_id,
                asset=asset,
                threshold=threshold,
                direction=direction,
                status=AlertStatus.ACTIVE,
                language_preference=language_preference
            )
            
            async with get_db_session() as session:
                session.add(alert)
                await session.commit()
                await session.refresh(alert)
                
            logger.info(f"Created alert {alert_id} for user {user_id}: {asset} {direction.value} {threshold}")
            return alert
            
        except SQLAlchemyError as e:
            logger.error(f"Database error creating alert: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating alert: {e}")
            return None
    
    
    @staticmethod
    async def get_alert_by_id(alert_id: str) -> Optional[Alert]:
        """Get a single alert by ID.
        
        Args:
            alert_id: Alert UUID
            
        Returns:
            Alert object or None if not found
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Alert).where(Alert.alert_id == alert_id)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting alert: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting alert: {e}")
            return None
    
    
    @staticmethod
    async def list_alerts_by_user(user_id: int, status: Optional[AlertStatus] = None) -> List[Alert]:
        """List all alerts for a specific user.
        
        Args:
            user_id: Telegram user ID
            status: Optional filter by status (if None, returns all)
            
        Returns:
            List of Alert objects
        """
        try:
            async with get_db_session() as session:
                query = select(Alert).where(Alert.user_id == user_id)
                
                if status is not None:
                    query = query.where(Alert.status == status)
                
                result = await session.execute(query)
                alerts = result.scalars().all()
                
            return alerts
            
        except SQLAlchemyError as e:
            logger.error(f"Database error listing alerts: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing alerts: {e}")
            return []
    
    
    @staticmethod
    async def list_active_alerts() -> List[Alert]:
        """List all active alerts across all users.
        
        Returns:
            List of Alert objects with ACTIVE status
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Alert).where(Alert.status == AlertStatus.ACTIVE)
                )
                alerts = result.scalars().all()
                
            return alerts
            
        except SQLAlchemyError as e:
            logger.error(f"Database error listing active alerts: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing active alerts: {e}")
            return []
    
    
    @staticmethod
    async def delete_alert(alert_id: str) -> bool:
        """Delete an alert by ID.
        
        Args:
            alert_id: Alert UUID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    delete(Alert).where(Alert.alert_id == alert_id)
                )
                await session.commit()
                
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted alert {alert_id}")
            else:
                logger.warning(f"Alert {alert_id} not found for deletion")
            
            return deleted
            
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting alert: {e}")
            return False
    
    
    @staticmethod
    async def update_alert_status(alert_id: str, new_status: AlertStatus) -> bool:
        """Update the status of an alert.
        
        Args:
            alert_id: Alert UUID
            new_status: New AlertStatus
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    update(Alert)
                    .where(Alert.alert_id == alert_id)
                    .values(status=new_status)
                )
                await session.commit()
                
            updated = result.rowcount > 0
            if updated:
                logger.info(f"Updated alert {alert_id} status to {new_status.value}")
            else:
                logger.warning(f"Alert {alert_id} not found for status update")
            
            return updated
            
        except SQLAlchemyError as e:
            logger.error(f"Database error updating alert status: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating alert status: {e}")
            return False
    
    
    @staticmethod
    async def delete_alerts_by_user(user_id: int) -> int:
        """Delete all alerts for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of alerts deleted
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    delete(Alert).where(Alert.user_id == user_id)
                )
                await session.commit()
                
            deleted_count = result.rowcount
            logger.info(f"Deleted {deleted_count} alerts for user {user_id}")
            
            return deleted_count
            
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting user alerts: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error deleting user alerts: {e}")
            return 0
    
    
    @staticmethod
    async def count_alerts_by_user(user_id: int) -> int:
        """Count total alerts for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Total number of alerts
        """
        try:
            alerts = await AlertRepository.list_alerts_by_user(user_id)
            return len(alerts)
            
        except Exception as e:
            logger.error(f"Error counting alerts: {e}")
            return 0
    
    
    @staticmethod
    async def get_alerts_by_asset(asset: str) -> List[Alert]:
        """Get all active alerts for a specific asset.
        
        Args:
            asset: Asset code ('btc', 'eth', 'usdt')
            
        Returns:
            List of Alert objects for the asset
        """
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Alert).where(
                        (Alert.asset == asset) &
                        (Alert.status == AlertStatus.ACTIVE)
                    )
                )
                alerts = result.scalars().all()
                
            return alerts
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting alerts by asset: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting alerts by asset: {e}")
            return []
