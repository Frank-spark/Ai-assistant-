"""Executive Dashboard for Reflex AI Assistant."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..storage.models import (
    User, Conversation, StrategicContext, Decision, 
    Meeting, CulturalMetrics, TeamAlignment
)
from ..storage.db import get_db_session
from ..analytics.telemetry import get_telemetry_service
from ..config import get_settings

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="src/frontend/templates")

@dataclass
class DashboardMetrics:
    """Dashboard metrics data structure."""
    total_conversations: int
    time_saved_hours: float
    tasks_automated: int
    culture_engagement_score: float
    decision_confidence_avg: float
    team_alignment_score: float
    recent_decisions: List[Dict[str, Any]]
    upcoming_meetings: List[Dict[str, Any]]
    cultural_insights: List[Dict[str, Any]]
    productivity_trends: List[Dict[str, Any]]


class ExecutiveDashboard:
    """Executive dashboard for Reflex AI Assistant."""
    
    def __init__(self):
        self.settings = get_settings()
        self.telemetry = get_telemetry_service()
        
    async def render_dashboard(self, request: Request, user_id: str) -> HTMLResponse:
        """Render the main executive dashboard."""
        try:
            # Get dashboard metrics
            metrics = await self._get_dashboard_metrics(user_id)
            
            # Get user context
            user_context = await self._get_user_context(user_id)
            
            return templates.TemplateResponse(
                "dashboard.html",
                {
                    "request": request,
                    "metrics": metrics,
                    "user": user_context,
                    "current_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "page_title": "Executive Dashboard - Reflex AI"
                }
            )
            
        except Exception as e:
            logger.error(f"Error rendering dashboard: {e}")
            raise HTTPException(status_code=500, detail="Dashboard error")
    
    async def render_analytics(self, request: Request, user_id: str) -> HTMLResponse:
        """Render analytics dashboard."""
        try:
            analytics_data = await self._get_analytics_data(user_id)
            
            return templates.TemplateResponse(
                "analytics.html",
                {
                    "request": request,
                    "analytics": analytics_data,
                    "page_title": "Analytics - Reflex AI"
                }
            )
            
        except Exception as e:
            logger.error(f"Error rendering analytics: {e}")
            raise HTTPException(status_code=500, detail="Analytics error")
    
    async def render_decisions(self, request: Request, user_id: str) -> HTMLResponse:
        """Render decisions dashboard."""
        try:
            decisions_data = await self._get_decisions_data(user_id)
            
            return templates.TemplateResponse(
                "decisions.html",
                {
                    "request": request,
                    "decisions": decisions_data,
                    "page_title": "Decision Intelligence - Reflex AI"
                }
            )
            
        except Exception as e:
            logger.error(f"Error rendering decisions: {e}")
            raise HTTPException(status_code=500, detail="Decisions error")
    
    async def render_culture(self, request: Request, user_id: str) -> HTMLResponse:
        """Render culture insights dashboard."""
        try:
            culture_data = await self._get_culture_data(user_id)
            
            return templates.TemplateResponse(
                "culture.html",
                {
                    "request": request,
                    "culture": culture_data,
                    "page_title": "Culture Insights - Reflex AI"
                }
            )
            
        except Exception as e:
            logger.error(f"Error rendering culture dashboard: {e}")
            raise HTTPException(status_code=500, detail="Culture dashboard error")
    
    async def _get_dashboard_metrics(self, user_id: str) -> DashboardMetrics:
        """Get comprehensive dashboard metrics."""
        try:
            db_session = get_db_session()
            
            # Get conversation metrics
            total_conversations = db_session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).count()
            
            # Calculate time saved (estimated 5 minutes per conversation)
            time_saved_hours = (total_conversations * 5) / 60
            
            # Get automated tasks (from strategic contexts)
            tasks_automated = db_session.query(StrategicContext).filter(
                StrategicContext.user_id == user_id,
                StrategicContext.context_type.in_(["task_creation", "email_draft", "meeting_schedule"])
            ).count()
            
            # Get culture engagement score
            recent_metrics = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.metric_category == "engagement",
                CulturalMetrics.created_at >= datetime.utcnow() - timedelta(days=30)
            ).order_by(CulturalMetrics.created_at.desc()).first()
            
            culture_engagement_score = recent_metrics.metric_value if recent_metrics else 75.0
            
            # Get decision confidence average
            recent_decisions = db_session.query(Decision).filter(
                Decision.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            decision_confidence_avg = sum(d.confidence_score for d in recent_decisions) / len(recent_decisions) if recent_decisions else 0.0
            
            # Get team alignment score
            team_alignments = db_session.query(TeamAlignment).filter(
                TeamAlignment.last_assessment >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            team_alignment_score = sum(a.alignment_score for a in team_alignments) / len(team_alignments) if team_alignments else 0.0
            
            # Get recent decisions
            recent_decisions_data = []
            for decision in recent_decisions[:5]:
                recent_decisions_data.append({
                    "id": str(decision.id),
                    "title": decision.title,
                    "type": decision.decision_type,
                    "status": decision.status,
                    "confidence": decision.confidence_score,
                    "amount": decision.amount,
                    "created_at": decision.created_at.strftime("%Y-%m-%d")
                })
            
            # Get upcoming meetings
            upcoming_meetings = db_session.query(Meeting).filter(
                Meeting.start_time >= datetime.utcnow(),
                Meeting.status == "scheduled"
            ).order_by(Meeting.start_time).limit(5).all()
            
            upcoming_meetings_data = []
            for meeting in upcoming_meetings:
                upcoming_meetings_data.append({
                    "id": str(meeting.id),
                    "title": meeting.title,
                    "type": meeting.meeting_type,
                    "start_time": meeting.start_time.strftime("%Y-%m-%d %H:%M"),
                    "participants": len(meeting.participants) if meeting.participants else 0
                })
            
            # Get cultural insights
            cultural_insights = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.created_at >= datetime.utcnow() - timedelta(days=7)
            ).order_by(CulturalMetrics.created_at.desc()).limit(3).all()
            
            cultural_insights_data = []
            for insight in cultural_insights:
                cultural_insights_data.append({
                    "metric": insight.metric_name,
                    "value": insight.metric_value,
                    "category": insight.metric_category,
                    "trend": insight.trend,
                    "date": insight.created_at.strftime("%Y-%m-%d")
                })
            
            # Get productivity trends (last 7 days)
            productivity_trends = []
            for i in range(7):
                date = datetime.utcnow() - timedelta(days=i)
                day_conversations = db_session.query(Conversation).filter(
                    Conversation.user_id == user_id,
                    func.date(Conversation.created_at) == date.date()
                ).count()
                
                productivity_trends.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "conversations": day_conversations,
                    "time_saved": day_conversations * 5  # 5 minutes per conversation
                })
            
            productivity_trends.reverse()  # Show oldest to newest
            
            db_session.close()
            
            return DashboardMetrics(
                total_conversations=total_conversations,
                time_saved_hours=round(time_saved_hours, 1),
                tasks_automated=tasks_automated,
                culture_engagement_score=round(culture_engagement_score, 1),
                decision_confidence_avg=round(decision_confidence_avg * 100, 1),
                team_alignment_score=round(team_alignment_score * 100, 1),
                recent_decisions=recent_decisions_data,
                upcoming_meetings=upcoming_meetings_data,
                cultural_insights=cultural_insights_data,
                productivity_trends=productivity_trends
            )
            
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return self._get_default_metrics()
    
    async def _get_analytics_data(self, user_id: str) -> Dict[str, Any]:
        """Get detailed analytics data."""
        try:
            db_session = get_db_session()
            
            # Get time-based analytics
            last_30_days = datetime.utcnow() - timedelta(days=30)
            
            # Conversation analytics
            conversations = db_session.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= last_30_days
            ).all()
            
            # Context injection analytics
            context_injections = db_session.query(StrategicContext).filter(
                StrategicContext.user_id == user_id,
                StrategicContext.created_at >= last_30_days
            ).all()
            
            # Decision analytics
            decisions = db_session.query(Decision).filter(
                Decision.created_at >= last_30_days
            ).all()
            
            # Cultural metrics
            cultural_metrics = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.created_at >= last_30_days
            ).all()
            
            db_session.close()
            
            return {
                "conversations": {
                    "total": len(conversations),
                    "avg_per_day": len(conversations) / 30,
                    "time_saved_hours": len(conversations) * 5 / 60
                },
                "context_injections": {
                    "total": len(context_injections),
                    "avg_alignment": sum(c.alignment_score for c in context_injections) / len(context_injections) if context_injections else 0,
                    "top_channels": self._get_top_channels(context_injections)
                },
                "decisions": {
                    "total": len(decisions),
                    "approved": len([d for d in decisions if d.status == "approved"]),
                    "avg_confidence": sum(d.confidence_score for d in decisions) / len(decisions) if decisions else 0
                },
                "culture": {
                    "metrics": len(cultural_metrics),
                    "avg_engagement": sum(m.metric_value for m in cultural_metrics if m.metric_category == "engagement") / len([m for m in cultural_metrics if m.metric_category == "engagement"]) if cultural_metrics else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return {}
    
    async def _get_decisions_data(self, user_id: str) -> Dict[str, Any]:
        """Get decisions dashboard data."""
        try:
            db_session = get_db_session()
            
            # Get recent decisions
            recent_decisions = db_session.query(Decision).order_by(
                Decision.created_at.desc()
            ).limit(20).all()
            
            # Get decision statistics
            total_decisions = db_session.query(Decision).count()
            pending_decisions = db_session.query(Decision).filter(
                Decision.status == "pending"
            ).count()
            approved_decisions = db_session.query(Decision).filter(
                Decision.status == "approved"
            ).count()
            
            # Get decision types breakdown
            decision_types = db_session.query(
                Decision.decision_type,
                func.count(Decision.id)
            ).group_by(Decision.decision_type).all()
            
            db_session.close()
            
            return {
                "recent_decisions": [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "type": d.decision_type,
                        "status": d.status,
                        "confidence": d.confidence_score,
                        "amount": d.amount,
                        "requester": d.requester,
                        "created_at": d.created_at.strftime("%Y-%m-%d %H:%M")
                    }
                    for d in recent_decisions
                ],
                "statistics": {
                    "total": total_decisions,
                    "pending": pending_decisions,
                    "approved": approved_decisions,
                    "approval_rate": (approved_decisions / total_decisions * 100) if total_decisions > 0 else 0
                },
                "decision_types": dict(decision_types)
            }
            
        except Exception as e:
            logger.error(f"Error getting decisions data: {e}")
            return {}
    
    async def _get_culture_data(self, user_id: str) -> Dict[str, Any]:
        """Get culture insights data."""
        try:
            db_session = get_db_session()
            
            # Get cultural metrics
            cultural_metrics = db_session.query(CulturalMetrics).order_by(
                CulturalMetrics.created_at.desc()
            ).limit(50).all()
            
            # Get team alignments
            team_alignments = db_session.query(TeamAlignment).order_by(
                TeamAlignment.last_assessment.desc()
            ).limit(20).all()
            
            # Get strategic contexts for cultural analysis
            cultural_contexts = db_session.query(StrategicContext).filter(
                StrategicContext.context_type.in_(["culture", "values", "well_being"])
            ).order_by(StrategicContext.created_at.desc()).limit(20).all()
            
            db_session.close()
            
            return {
                "metrics": [
                    {
                        "name": m.metric_name,
                        "value": m.metric_value,
                        "category": m.metric_category,
                        "trend": m.trend,
                        "date": m.created_at.strftime("%Y-%m-%d")
                    }
                    for m in cultural_metrics
                ],
                "team_alignments": [
                    {
                        "team": a.team_name,
                        "goal": a.goal_name,
                        "alignment": a.alignment_score,
                        "progress": a.progress_percentage,
                        "last_assessment": a.last_assessment.strftime("%Y-%m-%d")
                    }
                    for a in team_alignments
                ],
                "cultural_contexts": [
                    {
                        "type": c.context_type,
                        "channel": c.channel,
                        "alignment": c.alignment_score,
                        "cultural_relevance": c.cultural_relevance,
                        "date": c.created_at.strftime("%Y-%m-%d")
                    }
                    for c in cultural_contexts
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting culture data: {e}")
            return {}
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for dashboard."""
        try:
            db_session = get_db_session()
            
            user = db_session.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {"name": "Executive", "role": "CEO", "subscription": "Executive"}
            
            db_session.close()
            
            return {
                "name": user.name,
                "role": user.role,
                "subscription": user.subscription_tier,
                "email": user.email
            }
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"name": "Executive", "role": "CEO", "subscription": "Executive"}
    
    def _get_top_channels(self, context_injections: List[StrategicContext]) -> Dict[str, int]:
        """Get top channels for context injections."""
        channel_counts = {}
        for injection in context_injections:
            channel = injection.channel
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        return dict(sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    
    def _get_default_metrics(self) -> DashboardMetrics:
        """Get default metrics when database is unavailable."""
        return DashboardMetrics(
            total_conversations=0,
            time_saved_hours=0.0,
            tasks_automated=0,
            culture_engagement_score=75.0,
            decision_confidence_avg=85.0,
            team_alignment_score=80.0,
            recent_decisions=[],
            upcoming_meetings=[],
            cultural_insights=[],
            productivity_trends=[]
        )


# Global dashboard instance
dashboard = ExecutiveDashboard()


def get_dashboard() -> ExecutiveDashboard:
    """Get the global dashboard instance."""
    return dashboard 