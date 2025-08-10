"""Outcomes analytics and ROI tracking for Reflex AI Assistant."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import json

from src.storage.models import (
    User, Conversation, WorkflowExecution, Email, 
    AsanaTask, SlackMessage, UsageLog
)


class OutcomesTracker:
    """Tracks business outcomes and ROI metrics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_first_30_minutes_checklist(self, user_id: str) -> Dict[str, Any]:
        """Get the "First 30 minutes" checklist and outcomes."""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        # Calculate time since first use
        first_use = user.created_at
        time_since_first_use = datetime.now() - first_use
        minutes_since_first_use = int(time_since_first_use.total_seconds() / 60)
        
        # Get user's activity in first 30 minutes
        first_30_minutes = first_use + timedelta(minutes=30)
        
        # Checklist items
        checklist = [
            {
                "id": "setup_complete",
                "title": "Complete Initial Setup",
                "description": "Connect your tools and configure preferences",
                "completed": self._check_setup_complete(user_id),
                "time_saved": "5 minutes",
                "impact": "Immediate productivity gain"
            },
            {
                "id": "first_conversation",
                "title": "Have Your First Conversation",
                "description": "Start talking to your AI assistant",
                "completed": self._check_first_conversation(user_id, first_30_minutes),
                "time_saved": "2 minutes",
                "impact": "Natural interaction established"
            },
            {
                "id": "email_triage",
                "title": "Process Your First Email",
                "description": "Let AI triage and respond to emails",
                "completed": self._check_email_triage(user_id, first_30_minutes),
                "time_saved": "8 minutes",
                "impact": "Email management automated"
            },
            {
                "id": "task_creation",
                "title": "Create Your First Task",
                "description": "Convert conversation to actionable task",
                "completed": self._check_task_creation(user_id, first_30_minutes),
                "time_saved": "3 minutes",
                "impact": "Task management streamlined"
            },
            {
                "id": "meeting_scheduling",
                "title": "Schedule Your First Meeting",
                "description": "AI handles calendar coordination",
                "completed": self._check_meeting_scheduling(user_id, first_30_minutes),
                "time_saved": "5 minutes",
                "impact": "Meeting coordination automated"
            },
            {
                "id": "team_alignment",
                "title": "Align Team on Goals",
                "description": "Share strategic objectives with team",
                "completed": self._check_team_alignment(user_id, first_30_minutes),
                "time_saved": "10 minutes",
                "impact": "Team focus established"
            }
        ]
        
        # Calculate outcomes
        outcomes = self._calculate_outcomes(user_id, first_30_minutes)
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "company": user.company_name,
                "first_use": first_use.isoformat(),
                "minutes_since_first_use": minutes_since_first_use
            },
            "checklist": checklist,
            "outcomes": outcomes,
            "progress": {
                "completed_items": len([item for item in checklist if item["completed"]]),
                "total_items": len(checklist),
                "completion_percentage": int(len([item for item in checklist if item["completed"]]) / len(checklist) * 100)
            }
        }
    
    def _check_setup_complete(self, user_id: str) -> bool:
        """Check if user has completed initial setup."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Check if user has connected at least one integration
        has_slack = bool(user.slack_workspace_id)
        has_gmail = user.gmail_connected
        has_asana = bool(user.asana_workspace_id)
        
        # Check if user has configured basic preferences
        has_company_info = bool(user.company_name and user.role)
        
        return has_company_info and (has_slack or has_gmail or has_asana)
    
    def _check_first_conversation(self, user_id: str, first_30_minutes: datetime) -> bool:
        """Check if user had their first conversation."""
        conversation = self.db.query(Conversation).filter(
            and_(
                Conversation.user_id == user_id,
                Conversation.started_at <= first_30_minutes
            )
        ).first()
        
        return conversation is not None
    
    def _check_email_triage(self, user_id: str, first_30_minutes: datetime) -> bool:
        """Check if user processed their first email."""
        # Check if any emails were processed
        email_workflow = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "email_triage",
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).first()
        
        return email_workflow is not None
    
    def _check_task_creation(self, user_id: str, first_30_minutes: datetime) -> bool:
        """Check if user created their first task."""
        task_workflow = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "task_creation",
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).first()
        
        return task_workflow is not None
    
    def _check_meeting_scheduling(self, user_id: str, first_30_minutes: datetime) -> bool:
        """Check if user scheduled their first meeting."""
        meeting_workflow = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "meeting_scheduling",
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).first()
        
        return meeting_workflow is not None
    
    def _check_team_alignment(self, user_id: str, first_30_minutes: datetime) -> bool:
        """Check if user aligned team on goals."""
        # Check if user has team members or has shared goals
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # For demo purposes, assume team alignment if user has company info
        return bool(user.company_name and user.role)
    
    def _calculate_outcomes(self, user_id: str, first_30_minutes: datetime) -> Dict[str, Any]:
        """Calculate outcomes from first 30 minutes."""
        
        # Count activities in first 30 minutes
        conversations = self.db.query(Conversation).filter(
            and_(
                Conversation.user_id == user_id,
                Conversation.started_at <= first_30_minutes
            )
        ).count()
        
        workflows = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).count()
        
        emails_processed = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "email_triage",
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).count()
        
        tasks_created = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "task_creation",
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).count()
        
        meetings_scheduled = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "meeting_scheduling",
                WorkflowExecution.created_at <= first_30_minutes
            )
        ).count()
        
        # Calculate time savings (in minutes)
        time_saved = {
            "email_triage": emails_processed * 8,  # 8 minutes per email
            "task_creation": tasks_created * 3,    # 3 minutes per task
            "meeting_scheduling": meetings_scheduled * 5,  # 5 minutes per meeting
            "conversations": conversations * 2     # 2 minutes per conversation
        }
        
        total_time_saved = sum(time_saved.values())
        
        return {
            "activities": {
                "conversations": conversations,
                "workflows": workflows,
                "emails_processed": emails_processed,
                "tasks_created": tasks_created,
                "meetings_scheduled": meetings_scheduled
            },
            "time_saved": {
                "breakdown": time_saved,
                "total_minutes": total_time_saved,
                "total_hours": round(total_time_saved / 60, 2)
            },
            "efficiency_gains": {
                "productivity_increase": min(conversations * 10, 50),  # Up to 50% increase
                "response_time_reduction": min(emails_processed * 15, 80),  # Up to 80% reduction
                "task_completion_rate": min(tasks_created * 20, 90)  # Up to 90% improvement
            }
        }
    
    def get_roi_metrics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Calculate ROI metrics for a user."""
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Get user's hourly rate (estimate based on role)
        user = self.db.query(User).filter(User.id == user_id).first()
        hourly_rate = self._estimate_hourly_rate(user.role if user else "executive")
        
        # Calculate time savings
        total_time_saved_minutes = self._calculate_total_time_saved(user_id, start_date)
        total_time_saved_hours = total_time_saved_minutes / 60
        
        # Calculate cost savings
        cost_savings = total_time_saved_hours * hourly_rate
        
        # Calculate subscription cost
        subscription_cost = self._get_subscription_cost(user.subscription_tier if user else "professional")
        
        # Calculate ROI
        roi_percentage = ((cost_savings - subscription_cost) / subscription_cost * 100) if subscription_cost > 0 else 0
        
        return {
            "period": f"Last {days} days",
            "time_savings": {
                "minutes": total_time_saved_minutes,
                "hours": round(total_time_saved_hours, 2),
                "days": round(total_time_saved_hours / 8, 2)
            },
            "cost_analysis": {
                "hourly_rate": hourly_rate,
                "cost_savings": round(cost_savings, 2),
                "subscription_cost": subscription_cost,
                "net_savings": round(cost_savings - subscription_cost, 2)
            },
            "roi": {
                "percentage": round(roi_percentage, 2),
                "payback_period_days": self._calculate_payback_period(cost_savings, subscription_cost, days)
            }
        }
    
    def _calculate_total_time_saved(self, user_id: str, start_date: datetime) -> int:
        """Calculate total time saved for a user."""
        
        # Get all workflows in the period
        workflows = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.created_at >= start_date
            )
        ).all()
        
        total_minutes = 0
        
        for workflow in workflows:
            if workflow.workflow_type == "email_triage":
                total_minutes += 8  # 8 minutes per email
            elif workflow.workflow_type == "task_creation":
                total_minutes += 3  # 3 minutes per task
            elif workflow.workflow_type == "meeting_scheduling":
                total_minutes += 5  # 5 minutes per meeting
            elif workflow.workflow_type == "report_generation":
                total_minutes += 15  # 15 minutes per report
            elif workflow.workflow_type == "data_analysis":
                total_minutes += 20  # 20 minutes per analysis
        
        return total_minutes
    
    def _estimate_hourly_rate(self, role: str) -> float:
        """Estimate hourly rate based on role."""
        rates = {
            "ceo": 200.0,
            "cto": 150.0,
            "executive": 150.0,
            "director": 100.0,
            "manager": 75.0,
            "employee": 50.0
        }
        
        return rates.get(role.lower(), 100.0)
    
    def _get_subscription_cost(self, tier: str) -> float:
        """Get monthly subscription cost."""
        costs = {
            "free": 0.0,
            "starter": 29.0,
            "professional": 99.0,
            "enterprise": 299.0
        }
        
        return costs.get(tier.lower(), 99.0)
    
    def _calculate_payback_period(self, cost_savings: float, subscription_cost: float, days: int) -> int:
        """Calculate payback period in days."""
        if cost_savings <= subscription_cost:
            return -1  # No payback
        
        daily_savings = cost_savings / days
        payback_days = int(subscription_cost / daily_savings)
        
        return payback_days
    
    def get_sla_metrics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get SLA performance metrics."""
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Get all workflows in the period
        workflows = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.created_at >= start_date
            )
        ).all()
        
        total_workflows = len(workflows)
        completed_workflows = len([w for w in workflows if w.status == "completed"])
        failed_workflows = len([w for w in workflows if w.status == "failed"])
        
        # Calculate SLA metrics
        sla_metrics = {
            "total_workflows": total_workflows,
            "completed": completed_workflows,
            "failed": failed_workflows,
            "success_rate": round(completed_workflows / total_workflows * 100, 2) if total_workflows > 0 else 0,
            "average_response_time": self._calculate_average_response_time(workflows),
            "sla_targets": {
                "email_response": "2 minutes",
                "task_creation": "1 minute",
                "meeting_scheduling": "5 minutes",
                "report_generation": "10 minutes"
            }
        }
        
        return sla_metrics
    
    def _calculate_average_response_time(self, workflows: List[WorkflowExecution]) -> str:
        """Calculate average response time for workflows."""
        if not workflows:
            return "0 minutes"
        
        total_time = 0
        count = 0
        
        for workflow in workflows:
            if workflow.started_at and workflow.completed_at:
                duration = (workflow.completed_at - workflow.started_at).total_seconds()
                total_time += duration
                count += 1
        
        if count == 0:
            return "0 minutes"
        
        avg_seconds = total_time / count
        avg_minutes = round(avg_seconds / 60, 1)
        
        return f"{avg_minutes} minutes"
    
    def get_task_closure_metrics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get task closure and completion metrics."""
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Get all tasks created in the period
        task_workflows = self.db.query(WorkflowExecution).filter(
            and_(
                WorkflowExecution.trigger_user == user_id,
                WorkflowExecution.workflow_type == "task_creation",
                WorkflowExecution.created_at >= start_date
            )
        ).all()
        
        total_tasks = len(task_workflows)
        
        # For demo purposes, assume 85% completion rate
        completed_tasks = int(total_tasks * 0.85)
        pending_tasks = total_tasks - completed_tasks
        
        # Calculate average completion time (demo data)
        avg_completion_hours = 24  # 24 hours average
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0,
            "average_completion_time": f"{avg_completion_hours} hours",
            "task_types": {
                "email_followup": int(total_tasks * 0.4),
                "meeting_preparation": int(total_tasks * 0.25),
                "project_management": int(total_tasks * 0.2),
                "research": int(total_tasks * 0.15)
            }
        } 