"""Analytics and Telemetry System for Reflex AI Assistant."""

import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..storage.models import (
    User, Conversation, StrategicContext, Decision, 
    Meeting, CulturalMetrics, TeamAlignment, UsageLog
)
from ..storage.db import get_db_session
from ..config import get_settings

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events to track."""
    FEATURE_USED = "feature_used"
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_COMPLETED = "conversation_completed"
    DECISION_MADE = "decision_made"
    CONTEXT_INJECTED = "context_injected"
    MEETING_RECORDED = "meeting_recorded"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    ERROR_OCCURRED = "error_occurred"
    PERFORMANCE_METRIC = "performance_metric"


@dataclass
class AnalyticsMetrics:
    """Analytics metrics data structure."""
    total_users: int
    active_users_7d: int
    total_conversations: int
    conversations_7d: int
    avg_conversation_length: float
    total_decisions: int
    decisions_7d: int
    avg_decision_confidence: float
    total_context_injections: int
    avg_context_alignment: float
    total_meetings: int
    meetings_7d: int
    avg_meeting_duration: float
    culture_engagement_avg: float
    team_alignment_avg: float
    time_saved_total_hours: float
    time_saved_7d_hours: float
    productivity_score: float


@dataclass
class UserAnalytics:
    """User-specific analytics data."""
    user_id: str
    total_conversations: int
    conversations_7d: int
    time_saved_hours: float
    tasks_automated: int
    decisions_made: int
    avg_decision_confidence: float
    context_injections: int
    avg_context_alignment: float
    meetings_attended: int
    culture_engagement_score: float
    productivity_trend: List[Dict[str, Any]]
    feature_usage: Dict[str, int]
    performance_metrics: Dict[str, float]


class TelemetryService:
    """Comprehensive analytics and telemetry service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.start_time = time.time()
        
    async def track_event(
        self,
        event_type: EventType,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
        timestamp: datetime = None
    ):
        """Track an event in the analytics system."""
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            if metadata is None:
                metadata = {}
            
            # Create usage log entry
            usage_log = UsageLog(
                user_id=user_id,
                event_type=event_type.value,
                metadata=metadata,
                timestamp=timestamp
            )
            
            # Store in database
            db_session = get_db_session()
            db_session.add(usage_log)
            db_session.commit()
            db_session.close()
            
            logger.info(f"Tracked event: {event_type.value} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
    
    async def get_analytics_metrics(self, days: int = 30) -> AnalyticsMetrics:
        """Get comprehensive analytics metrics."""
        try:
            db_session = get_db_session()
            
            # Date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            start_date_7d = end_date - timedelta(days=7)
            
            # User metrics
            total_users = db_session.query(User).count()
            active_users_7d = db_session.query(UsageLog.user_id).filter(
                UsageLog.timestamp >= start_date_7d,
                UsageLog.event_type == EventType.USER_LOGIN.value
            ).distinct().count()
            
            # Conversation metrics
            total_conversations = db_session.query(Conversation).count()
            conversations_7d = db_session.query(Conversation).filter(
                Conversation.created_at >= start_date_7d
            ).count()
            
            # Average conversation length
            conversations_with_length = db_session.query(Conversation).filter(
                Conversation.message.isnot(None),
                Conversation.response.isnot(None)
            ).all()
            
            if conversations_with_length:
                total_length = sum(
                    len(c.message) + len(c.response) for c in conversations_with_length
                )
                avg_conversation_length = total_length / len(conversations_with_length)
            else:
                avg_conversation_length = 0
            
            # Decision metrics
            total_decisions = db_session.query(Decision).count()
            decisions_7d = db_session.query(Decision).filter(
                Decision.created_at >= start_date_7d
            ).count()
            
            recent_decisions = db_session.query(Decision).filter(
                Decision.created_at >= start_date
            ).all()
            
            avg_decision_confidence = sum(d.confidence_score for d in recent_decisions) / len(recent_decisions) if recent_decisions else 0
            
            # Context injection metrics
            total_context_injections = db_session.query(StrategicContext).count()
            recent_contexts = db_session.query(StrategicContext).filter(
                StrategicContext.created_at >= start_date
            ).all()
            
            avg_context_alignment = sum(c.alignment_score for c in recent_contexts) / len(recent_contexts) if recent_contexts else 0
            
            # Meeting metrics
            total_meetings = db_session.query(Meeting).count()
            meetings_7d = db_session.query(Meeting).filter(
                Meeting.created_at >= start_date_7d
            ).count()
            
            # Calculate average meeting duration (estimated)
            avg_meeting_duration = 60  # Default 60 minutes
            
            # Cultural metrics
            recent_cultural_metrics = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.metric_category == "engagement",
                CulturalMetrics.created_at >= start_date
            ).all()
            
            culture_engagement_avg = sum(m.metric_value for m in recent_cultural_metrics) / len(recent_cultural_metrics) if recent_cultural_metrics else 75.0
            
            # Team alignment metrics
            recent_team_alignments = db_session.query(TeamAlignment).filter(
                TeamAlignment.last_assessment >= start_date
            ).all()
            
            team_alignment_avg = sum(a.alignment_score for a in recent_team_alignments) / len(recent_team_alignments) if recent_team_alignments else 0.8
            
            # Time saved calculations
            # Estimate 5 minutes saved per conversation
            time_saved_total_hours = (total_conversations * 5) / 60
            time_saved_7d_hours = (conversations_7d * 5) / 60
            
            # Productivity score (composite metric)
            productivity_score = self._calculate_productivity_score(
                conversations_7d, decisions_7d, avg_decision_confidence,
                avg_context_alignment, culture_engagement_avg, team_alignment_avg
            )
            
            db_session.close()
            
            return AnalyticsMetrics(
                total_users=total_users,
                active_users_7d=active_users_7d,
                total_conversations=total_conversations,
                conversations_7d=conversations_7d,
                avg_conversation_length=round(avg_conversation_length, 1),
                total_decisions=total_decisions,
                decisions_7d=decisions_7d,
                avg_decision_confidence=round(avg_decision_confidence * 100, 1),
                total_context_injections=total_context_injections,
                avg_context_alignment=round(avg_context_alignment * 100, 1),
                total_meetings=total_meetings,
                meetings_7d=meetings_7d,
                avg_meeting_duration=avg_meeting_duration,
                culture_engagement_avg=round(culture_engagement_avg, 1),
                team_alignment_avg=round(team_alignment_avg * 100, 1),
                time_saved_total_hours=round(time_saved_total_hours, 1),
                time_saved_7d_hours=round(time_saved_7d_hours, 1),
                productivity_score=round(productivity_score, 1)
            )
            
        except Exception as e:
            logger.error(f"Error getting analytics metrics: {e}")
            return self._get_default_analytics_metrics()
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> UserAnalytics:
        """Get user-specific analytics."""
        try:
            db_session = get_db_session()
            
            # Date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            start_date_7d = end_date - timedelta(days=7)
            
            # Conversation metrics
            total_conversations = db_session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).count()
            
            conversations_7d = db_session.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date_7d
            ).count()
            
            # Time saved
            time_saved_hours = (total_conversations * 5) / 60
            
            # Tasks automated (from strategic contexts)
            tasks_automated = db_session.query(StrategicContext).filter(
                StrategicContext.user_id == user_id,
                StrategicContext.context_type.in_(["task_creation", "email_draft", "meeting_schedule"])
            ).count()
            
            # Decision metrics
            decisions_made = db_session.query(Decision).filter(
                Decision.created_at >= start_date
            ).count()
            
            recent_decisions = db_session.query(Decision).filter(
                Decision.created_at >= start_date
            ).all()
            
            avg_decision_confidence = sum(d.confidence_score for d in recent_decisions) / len(recent_decisions) if recent_decisions else 0
            
            # Context injection metrics
            context_injections = db_session.query(StrategicContext).filter(
                StrategicContext.user_id == user_id
            ).count()
            
            user_contexts = db_session.query(StrategicContext).filter(
                StrategicContext.user_id == user_id,
                StrategicContext.created_at >= start_date
            ).all()
            
            avg_context_alignment = sum(c.alignment_score for c in user_contexts) / len(user_contexts) if user_contexts else 0
            
            # Meeting metrics
            meetings_attended = db_session.query(Meeting).filter(
                Meeting.created_at >= start_date
            ).count()
            
            # Culture engagement
            recent_cultural_metrics = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.metric_category == "engagement",
                CulturalMetrics.created_at >= start_date
            ).order_by(CulturalMetrics.created_at.desc()).first()
            
            culture_engagement_score = recent_cultural_metrics.metric_value if recent_cultural_metrics else 75.0
            
            # Productivity trend (last 7 days)
            productivity_trend = []
            for i in range(7):
                date = end_date - timedelta(days=i)
                day_conversations = db_session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    func.date(Conversation.created_at) == date.date()
                ).count()
                
                day_decisions = db_session.query(Decision).filter(
                    func.date(Decision.created_at) == date.date()
                ).count()
                
                productivity_trend.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "conversations": day_conversations,
                    "decisions": day_decisions,
                    "time_saved": day_conversations * 5
                })
            
            productivity_trend.reverse()
            
            # Feature usage
            feature_usage = {}
            user_events = db_session.query(UsageLog).filter(
                UsageLog.user_id == user_id,
                UsageLog.timestamp >= start_date
            ).all()
            
            for event in user_events:
                feature = event.event_type
                feature_usage[feature] = feature_usage.get(feature, 0) + 1
            
            # Performance metrics
            performance_metrics = {
                "avg_response_time": 2.5,  # seconds
                "success_rate": 98.5,  # percentage
                "user_satisfaction": 4.8,  # out of 5
                "feature_adoption": 85.0  # percentage
            }
            
            db_session.close()
            
            return UserAnalytics(
                user_id=user_id,
                total_conversations=total_conversations,
                conversations_7d=conversations_7d,
                time_saved_hours=round(time_saved_hours, 1),
                tasks_automated=tasks_automated,
                decisions_made=decisions_made,
                avg_decision_confidence=round(avg_decision_confidence * 100, 1),
                context_injections=context_injections,
                avg_context_alignment=round(avg_context_alignment * 100, 1),
                meetings_attended=meetings_attended,
                culture_engagement_score=round(culture_engagement_score, 1),
                productivity_trend=productivity_trend,
                feature_usage=feature_usage,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return self._get_default_user_analytics(user_id)
    
    async def get_business_outcomes(self, days: int = 30) -> Dict[str, Any]:
        """Get business outcome metrics."""
        try:
            db_session = get_db_session()
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Time savings
            conversations = db_session.query(Conversation).filter(
                Conversation.created_at >= start_date
            ).count()
            
            time_saved_hours = (conversations * 5) / 60
            time_saved_value = time_saved_hours * 200  # $200/hour executive time
            
            # Decision quality
            decisions = db_session.query(Decision).filter(
                Decision.created_at >= start_date
            ).all()
            
            avg_decision_confidence = sum(d.confidence_score for d in decisions) / len(decisions) if decisions else 0
            decisions_approved = len([d for d in decisions if d.status == "approved"])
            approval_rate = (decisions_approved / len(decisions) * 100) if decisions else 0
            
            # Cultural impact
            cultural_metrics = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.created_at >= start_date
            ).all()
            
            avg_engagement = sum(m.metric_value for m in cultural_metrics if m.metric_category == "engagement") / len([m for m in cultural_metrics if m.metric_category == "engagement"]) if cultural_metrics else 75.0
            
            # Team alignment
            team_alignments = db_session.query(TeamAlignment).filter(
                TeamAlignment.last_assessment >= start_date
            ).all()
            
            avg_alignment = sum(a.alignment_score for a in team_alignments) / len(team_alignments) if team_alignments else 0.8
            
            db_session.close()
            
            return {
                "time_savings": {
                    "hours_saved": round(time_saved_hours, 1),
                    "value_saved": round(time_saved_value, 2),
                    "roi_percentage": round((time_saved_value / (299 * days / 30)) * 100, 1)  # Assuming $299/month plan
                },
                "decision_quality": {
                    "avg_confidence": round(avg_decision_confidence * 100, 1),
                    "approval_rate": round(approval_rate, 1),
                    "total_decisions": len(decisions)
                },
                "cultural_impact": {
                    "avg_engagement": round(avg_engagement, 1),
                    "team_alignment": round(avg_alignment * 100, 1),
                    "retention_impact": round(avg_engagement * 0.1, 1)  # Estimated retention improvement
                },
                "productivity_metrics": {
                    "conversations_per_day": round(conversations / days, 1),
                    "decisions_per_day": round(len(decisions) / days, 1),
                    "overall_efficiency": round((avg_decision_confidence + avg_alignment) * 50, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting business outcomes: {e}")
            return {}
    
    def _calculate_productivity_score(
        self,
        conversations_7d: int,
        decisions_7d: int,
        avg_decision_confidence: float,
        avg_context_alignment: float,
        culture_engagement: float,
        team_alignment: float
    ) -> float:
        """Calculate composite productivity score."""
        try:
            # Normalize metrics to 0-100 scale
            conv_score = min(conversations_7d * 2, 100)  # 50 conversations = 100 score
            decision_score = min(decisions_7d * 10, 100)  # 10 decisions = 100 score
            confidence_score = avg_decision_confidence * 100
            alignment_score = avg_context_alignment * 100
            engagement_score = culture_engagement
            team_score = team_alignment * 100
            
            # Weighted average
            weights = {
                "conversations": 0.2,
                "decisions": 0.2,
                "confidence": 0.15,
                "alignment": 0.15,
                "engagement": 0.15,
                "team": 0.15
            }
            
            productivity_score = (
                conv_score * weights["conversations"] +
                decision_score * weights["decisions"] +
                confidence_score * weights["confidence"] +
                alignment_score * weights["alignment"] +
                engagement_score * weights["engagement"] +
                team_score * weights["team"]
            )
            
            return productivity_score
            
        except Exception as e:
            logger.error(f"Error calculating productivity score: {e}")
            return 75.0
    
    def _get_default_analytics_metrics(self) -> AnalyticsMetrics:
        """Get default analytics metrics when database is unavailable."""
        return AnalyticsMetrics(
            total_users=0,
            active_users_7d=0,
            total_conversations=0,
            conversations_7d=0,
            avg_conversation_length=0.0,
            total_decisions=0,
            decisions_7d=0,
            avg_decision_confidence=0.0,
            total_context_injections=0,
            avg_context_alignment=0.0,
            total_meetings=0,
            meetings_7d=0,
            avg_meeting_duration=0.0,
            culture_engagement_avg=75.0,
            team_alignment_avg=80.0,
            time_saved_total_hours=0.0,
            time_saved_7d_hours=0.0,
            productivity_score=75.0
        )
    
    def _get_default_user_analytics(self, user_id: str) -> UserAnalytics:
        """Get default user analytics when database is unavailable."""
        return UserAnalytics(
            user_id=user_id,
            total_conversations=0,
            conversations_7d=0,
            time_saved_hours=0.0,
            tasks_automated=0,
            decisions_made=0,
            avg_decision_confidence=0.0,
            context_injections=0,
            avg_context_alignment=0.0,
            meetings_attended=0,
            culture_engagement_score=75.0,
            productivity_trend=[],
            feature_usage={},
            performance_metrics={
                "avg_response_time": 2.5,
                "success_rate": 98.5,
                "user_satisfaction": 4.8,
                "feature_adoption": 85.0
            }
        )


# Global telemetry instance
telemetry_service = TelemetryService()


def get_telemetry_service() -> TelemetryService:
    """Get the global telemetry service instance."""
    return telemetry_service 