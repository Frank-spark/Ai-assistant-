"""Comprehensive telemetry and usage analytics system."""

import logging
import time
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.storage.db import get_db_session
from src.saas.models import UsageLog, User
from src.config import get_settings

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events to track."""
    # User Events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_registration"
    USER_UPGRADE = "user_upgrade"
    USER_DOWNGRADE = "user_downgrade"
    
    # AI Events
    AI_CONVERSATION_START = "ai_conversation_start"
    AI_CONVERSATION_END = "ai_conversation_end"
    AI_RESPONSE_GENERATED = "ai_response_generated"
    AI_ERROR = "ai_error"
    AI_MODEL_SWITCH = "ai_model_switch"
    
    # Feature Events
    FEATURE_USED = "feature_used"
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_EXECUTED = "workflow_executed"
    
    # System Events
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ALERT = "performance_alert"
    SECURITY_EVENT = "security_event"


@dataclass
class TelemetryEvent:
    """Standardized telemetry event."""
    event_type: EventType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    source: str = "reflex_ai"
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PerformanceMetrics:
    """Performance metrics for tracking."""
    response_time: float
    tokens_used: int
    cost: float
    model_name: str
    success: bool
    error_message: Optional[str] = None


class TelemetryService:
    """Comprehensive telemetry and analytics service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.session_cache: Dict[str, Dict[str, Any]] = {}
        self.event_buffer: List[TelemetryEvent] = []
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
        
        # Start background tasks
        asyncio.create_task(self._periodic_flush())
    
    async def track_event(self, 
                         event_type: EventType,
                         user_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Track a telemetry event."""
        try:
            event = TelemetryEvent(
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {}
            )
            
            # Add to buffer
            self.event_buffer.append(event)
            
            # Flush if buffer is full
            if len(self.event_buffer) >= self.buffer_size:
                await self._flush_events()
                
        except Exception as e:
            logger.error(f"Failed to track event: {e}")
    
    async def track_ai_performance(self,
                                 user_id: str,
                                 model_name: str,
                                 performance: PerformanceMetrics):
        """Track AI performance metrics."""
        try:
            metadata = {
                "model_name": model_name,
                "response_time": performance.response_time,
                "tokens_used": performance.tokens_used,
                "cost": performance.cost,
                "success": performance.success,
                "error_message": performance.error_message
            }
            
            await self.track_event(
                EventType.AI_RESPONSE_GENERATED,
                user_id=user_id,
                metadata=metadata
            )
            
            # Also log to usage table
            await self._log_usage(user_id, "ai_response", metadata)
            
        except Exception as e:
            logger.error(f"Failed to track AI performance: {e}")
    
    async def track_user_activity(self,
                                user_id: str,
                                activity_type: str,
                                metadata: Optional[Dict[str, Any]] = None):
        """Track user activity."""
        try:
            event_type_map = {
                "login": EventType.USER_LOGIN,
                "logout": EventType.USER_LOGOUT,
                "register": EventType.USER_REGISTER,
                "upgrade": EventType.USER_UPGRADE,
                "downgrade": EventType.USER_DOWNGRADE,
                "feature_use": EventType.FEATURE_USED
            }
            
            event_type = event_type_map.get(activity_type, EventType.FEATURE_USED)
            
            await self.track_event(
                event_type,
                user_id=user_id,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Failed to track user activity: {e}")
    
    async def track_integration_event(self,
                                    user_id: str,
                                    integration_name: str,
                                    action: str,
                                    success: bool,
                                    metadata: Optional[Dict[str, Any]] = None):
        """Track integration events."""
        try:
            event_type = EventType.INTEGRATION_CONNECTED if action == "connect" else EventType.INTEGRATION_DISCONNECTED
            
            event_metadata = {
                "integration": integration_name,
                "action": action,
                "success": success,
                **(metadata or {})
            }
            
            await self.track_event(
                event_type,
                user_id=user_id,
                metadata=event_metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to track integration event: {e}")
    
    async def track_workflow_event(self,
                                 user_id: str,
                                 workflow_id: str,
                                 action: str,
                                 success: bool,
                                 metadata: Optional[Dict[str, Any]] = None):
        """Track workflow events."""
        try:
            event_type = EventType.WORKFLOW_CREATED if action == "create" else EventType.WORKFLOW_EXECUTED
            
            event_metadata = {
                "workflow_id": workflow_id,
                "action": action,
                "success": success,
                **(metadata or {})
            }
            
            await self.track_event(
                event_type,
                user_id=user_id,
                metadata=event_metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to track workflow event: {e}")
    
    async def track_error(self,
                         error_type: str,
                         error_message: str,
                         user_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Track error events."""
        try:
            event_metadata = {
                "error_type": error_type,
                "error_message": error_message,
                **(metadata or {})
            }
            
            await self.track_event(
                EventType.SYSTEM_ERROR,
                user_id=user_id,
                metadata=event_metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to track error: {e}")
    
    async def _log_usage(self, user_id: str, usage_type: str, metadata: Dict[str, Any]):
        """Log usage to the database."""
        try:
            db = next(get_db_session())
            
            usage_log = UsageLog(
                user_id=user_id,
                usage_type=usage_type,
                resource_id=metadata.get("resource_id"),
                platform=metadata.get("platform"),
                tokens_used=metadata.get("tokens_used", 0),
                api_calls=metadata.get("api_calls", 1),
                duration_seconds=metadata.get("response_time", 0.0),
                estimated_cost=metadata.get("cost", 0.0),
                metadata=metadata
            )
            
            db.add(usage_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
    
    async def _flush_events(self):
        """Flush buffered events to storage."""
        try:
            if not self.event_buffer:
                return
            
            # Convert events to JSON for storage
            events_data = []
            for event in self.event_buffer:
                event_dict = asdict(event)
                event_dict["event_type"] = event.event_type.value
                events_data.append(event_dict)
            
            # Store events (could be to database, file, or external service)
            await self._store_events(events_data)
            
            # Clear buffer
            self.event_buffer.clear()
            
        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
    
    async def _store_events(self, events_data: List[Dict[str, Any]]):
        """Store events to persistent storage."""
        try:
            # For now, log to file (in production, use database or external service)
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"logs/telemetry_{timestamp}.jsonl"
            
            with open(filename, "a") as f:
                for event in events_data:
                    f.write(json.dumps(event, default=str) + "\n")
            
        except Exception as e:
            logger.error(f"Failed to store events: {e}")
    
    async def _periodic_flush(self):
        """Periodically flush events."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_events()
            except Exception as e:
                logger.error(f"Periodic flush failed: {e}")
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific user."""
        try:
            db = next(get_db_session())
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get usage statistics
            usage_stats = db.query(
                UsageLog.usage_type,
                func.count(UsageLog.id).label('count'),
                func.sum(UsageLog.tokens_used).label('total_tokens'),
                func.sum(UsageLog.estimated_cost).label('total_cost'),
                func.avg(UsageLog.duration_seconds).label('avg_response_time')
            ).filter(
                and_(
                    UsageLog.user_id == user_id,
                    UsageLog.created_at >= start_date
                )
            ).group_by(UsageLog.usage_type).all()
            
            # Get daily activity
            daily_activity = db.query(
                func.date(UsageLog.created_at).label('date'),
                func.count(UsageLog.id).label('count')
            ).filter(
                and_(
                    UsageLog.user_id == user_id,
                    UsageLog.created_at >= start_date
                )
            ).group_by(func.date(UsageLog.created_at)).all()
            
            return {
                "user_id": user_id,
                "period_days": days,
                "usage_stats": [
                    {
                        "type": stat.usage_type,
                        "count": stat.count,
                        "total_tokens": stat.total_tokens or 0,
                        "total_cost": float(stat.total_cost or 0),
                        "avg_response_time": float(stat.avg_response_time or 0)
                    }
                    for stat in usage_stats
                ],
                "daily_activity": [
                    {
                        "date": str(activity.date),
                        "count": activity.count
                    }
                    for activity in daily_activity
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get user analytics: {e}")
            return {}
    
    async def get_system_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get system-wide analytics."""
        try:
            db = next(get_db_session())
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Overall usage statistics
            total_usage = db.query(
                func.count(UsageLog.id).label('total_events'),
                func.sum(UsageLog.tokens_used).label('total_tokens'),
                func.sum(UsageLog.estimated_cost).label('total_cost'),
                func.avg(UsageLog.duration_seconds).label('avg_response_time')
            ).filter(UsageLog.created_at >= start_date).first()
            
            # Usage by type
            usage_by_type = db.query(
                UsageLog.usage_type,
                func.count(UsageLog.id).label('count')
            ).filter(UsageLog.created_at >= start_date).group_by(UsageLog.usage_type).all()
            
            # Active users
            active_users = db.query(
                func.count(func.distinct(UsageLog.user_id)).label('active_users')
            ).filter(UsageLog.created_at >= start_date).first()
            
            return {
                "period_days": days,
                "total_events": total_usage.total_events or 0,
                "total_tokens": total_usage.total_tokens or 0,
                "total_cost": float(total_usage.total_cost or 0),
                "avg_response_time": float(total_usage.avg_response_time or 0),
                "active_users": active_users.active_users or 0,
                "usage_by_type": [
                    {
                        "type": stat.usage_type,
                        "count": stat.count
                    }
                    for stat in usage_by_type
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get system analytics: {e}")
            return {}
    
    async def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        try:
            db = next(get_db_session())
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Response time percentiles
            response_times = db.query(UsageLog.duration_seconds).filter(
                and_(
                    UsageLog.created_at >= start_time,
                    UsageLog.duration_seconds > 0
                )
            ).all()
            
            if response_times:
                times = [float(rt.duration_seconds) for rt in response_times]
                times.sort()
                
                p50 = times[len(times) // 2]
                p95 = times[int(len(times) * 0.95)]
                p99 = times[int(len(times) * 0.99)]
            else:
                p50 = p95 = p99 = 0
            
            # Error rate
            total_requests = db.query(func.count(UsageLog.id)).filter(
                UsageLog.created_at >= start_time
            ).scalar() or 0
            
            error_requests = db.query(func.count(UsageLog.id)).filter(
                and_(
                    UsageLog.created_at >= start_time,
                    UsageLog.metadata.contains({"error": True})
                )
            ).scalar() or 0
            
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "period_hours": hours,
                "response_time_p50": p50,
                "response_time_p95": p95,
                "response_time_p99": p99,
                "error_rate_percent": error_rate,
                "total_requests": total_requests,
                "error_requests": error_requests
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}


# Global instance
telemetry_service = None


def get_telemetry_service() -> TelemetryService:
    """Get the global telemetry service instance."""
    global telemetry_service
    if telemetry_service is None:
        telemetry_service = TelemetryService()
    return telemetry_service


async def init_telemetry_service():
    """Initialize the telemetry service."""
    global telemetry_service
    telemetry_service = TelemetryService()
    logger.info("Telemetry service initialized")
    return telemetry_service


# Decorator for automatic tracking
def track_function_call(event_type: EventType):
    """Decorator to automatically track function calls."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Extract user_id from args if available
                user_id = None
                if args and hasattr(args[0], 'user_id'):
                    user_id = args[0].user_id
                
                # Track the event
                telemetry = get_telemetry_service()
                await telemetry.track_event(
                    event_type,
                    user_id=user_id,
                    metadata={
                        "function": func.__name__,
                        "duration": time.time() - start_time,
                        "success": success,
                        "error_message": error_message
                    }
                )
        
        return wrapper
    return decorator 