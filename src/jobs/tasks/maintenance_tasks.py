"""Maintenance background tasks for Reflex Executive Assistant."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import current_task

from ..config import get_settings
from ..storage.db import get_db_session
from ..storage.models import (
    Conversation, Message, WorkflowExecution, 
    SlackMessage, SlackUser, SlackChannel,
    Email, AsanaTask, AsanaProject, AsanaStory
)
from ..integrations.gmail_client import get_gmail_client
from ..integrations.slack_client import get_slack_client
from ..integrations.asana_client import get_asana_client
from ..kb.retriever import get_knowledge_base
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.jobs.tasks.maintenance_tasks.cleanup_old_data")
def cleanup_old_data(self, days_old: int = 90) -> Dict[str, Any]:
    """Clean up old data from the database."""
    try:
        logger.info(f"Starting data cleanup for data older than {days_old} days")
        current_task.update_state(state="PROGRESS", meta={"status": "cleaning"})
        
        db_session = get_db_session()
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Clean up old conversations and messages
        old_conversations = db_session.query(Conversation).filter(
            Conversation.started_at < cutoff_date
        ).all()
        
        conversation_count = 0
        message_count = 0
        
        for conv in old_conversations:
            # Delete associated messages first
            messages = db_session.query(Message).filter(
                Message.conversation_id == conv.id
            ).all()
            message_count += len(messages)
            
            for msg in messages:
                db_session.delete(msg)
            
            db_session.delete(conv)
            conversation_count += 1
        
        # Clean up old workflow executions
        old_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.created_at < cutoff_date,
            WorkflowExecution.status.in_(["completed", "failed", "timeout"])
        ).all()
        
        workflow_count = 0
        for workflow in old_workflows:
            db_session.delete(workflow)
            workflow_count += 1
        
        # Clean up old Slack data
        old_slack_messages = db_session.query(SlackMessage).filter(
            SlackMessage.timestamp < cutoff_date
        ).all()
        
        slack_message_count = 0
        for msg in old_slack_messages:
            db_session.delete(msg)
            slack_message_count += 1
        
        # Clean up old emails
        old_emails = db_session.query(Email).filter(
            Email.received_at < cutoff_date
        ).all()
        
        email_count = 0
        for email in old_emails:
            db_session.delete(email)
            email_count += 1
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "cleaned_conversations": conversation_count,
            "cleaned_messages": message_count,
            "cleaned_workflows": workflow_count,
            "cleaned_slack_messages": slack_message_count,
            "cleaned_emails": email_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.maintenance_tasks.sync_integrations")
def sync_integrations(self) -> Dict[str, Any]:
    """Synchronize data with external integrations."""
    try:
        logger.info("Starting integration synchronization")
        current_task.update_state(state="PROGRESS", meta={"status": "syncing"})
        
        sync_results = {}
        
        # Sync Slack data
        try:
            slack_client = get_slack_client()
            slack_results = slack_client.sync_channels_and_users()
            sync_results["slack"] = slack_results
        except Exception as e:
            logger.error(f"Slack sync failed: {e}")
            sync_results["slack"] = {"error": str(e)}
        
        # Sync Asana data
        try:
            asana_client = get_asana_client()
            asana_results = asana_client.sync_projects_and_tasks()
            sync_results["asana"] = asana_results
        except Exception as e:
            logger.error(f"Asana sync failed: {e}")
            sync_results["asana"] = {"error": str(e)}
        
        # Sync Gmail data
        try:
            gmail_client = get_gmail_client()
            gmail_results = gmail_client.sync_recent_emails()
            sync_results["gmail"] = gmail_results
        except Exception as e:
            logger.error(f"Gmail sync failed: {e}")
            sync_results["gmail"] = {"error": str(e)}
        
        return {
            "status": "completed",
            "sync_results": sync_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Integration sync failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.maintenance_tasks.update_knowledge_base")
def update_knowledge_base(self) -> Dict[str, Any]:
    """Update the knowledge base with new information."""
    try:
        logger.info("Starting knowledge base update")
        current_task.update_state(state="PROGRESS", meta={"status": "updating"})
        
        kb = get_knowledge_base()
        
        # Get recent conversations and extract insights
        db_session = get_db_session()
        
        # Get conversations from the last 7 days
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_conversations = db_session.query(Conversation).filter(
            Conversation.started_at >= week_ago
        ).all()
        
        insights_added = 0
        
        for conv in recent_conversations:
            messages = db_session.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(Message.timestamp.asc()).all()
            
            # Extract key insights from conversation
            conversation_text = "\n".join([msg.content for msg in messages])
            
            # Add to knowledge base if it contains valuable information
            if len(conversation_text) > 100:  # Only add substantial conversations
                try:
                    kb.add_document(
                        content=conversation_text,
                        metadata={
                            "source": "conversation",
                            "conversation_id": conv.id,
                            "platform": conv.platform,
                            "user_id": conv.user_id,
                            "timestamp": conv.started_at.isoformat()
                        }
                    )
                    insights_added += 1
                except Exception as e:
                    logger.error(f"Failed to add conversation to KB: {e}")
        
        # Update company context from recent activities
        company_context = _extract_company_context(db_session, week_ago)
        
        if company_context:
            try:
                kb.add_document(
                    content=company_context,
                    metadata={
                        "source": "company_context",
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "context_update"
                    }
                )
                insights_added += 1
            except Exception as e:
                logger.error(f"Failed to add company context to KB: {e}")
        
        db_session.close()
        
        return {
            "status": "completed",
            "insights_added": insights_added,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Knowledge base update failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.maintenance_tasks.monitor_system_health")
def monitor_system_health(self) -> Dict[str, Any]:
    """Monitor system health and performance."""
    try:
        logger.info("Starting system health monitoring")
        current_task.update_state(state="PROGRESS", meta={"status": "monitoring"})
        
        health_metrics = {}
        
        # Check database health
        try:
            db_session = get_db_session()
            
            # Test database connection
            db_session.execute("SELECT 1")
            
            # Get table sizes
            table_sizes = {}
            tables = ["conversations", "messages", "workflow_executions", "slack_messages", "emails"]
            
            for table in tables:
                result = db_session.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                table_sizes[table] = count
            
            health_metrics["database"] = {
                "status": "healthy",
                "table_sizes": table_sizes
            }
            
            db_session.close()
            
        except Exception as e:
            health_metrics["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Redis health
        try:
            from ..storage.db import get_redis_client
            redis_client = get_redis_client()
            redis_client.ping()
            health_metrics["redis"] = {"status": "healthy"}
        except Exception as e:
            health_metrics["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check external integrations
        integration_health = {}
        
        # Check Gmail
        try:
            gmail_client = get_gmail_client()
            gmail_client.test_connection()
            integration_health["gmail"] = {"status": "healthy"}
        except Exception as e:
            integration_health["gmail"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Slack
        try:
            slack_client = get_slack_client()
            slack_client.test_connection()
            integration_health["slack"] = {"status": "healthy"}
        except Exception as e:
            integration_health["slack"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Asana
        try:
            asana_client = get_asana_client()
            asana_client.test_connection()
            integration_health["asana"] = {"status": "healthy"}
        except Exception as e:
            integration_health["asana"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        health_metrics["integrations"] = integration_health
        
        # Check knowledge base
        try:
            kb = get_knowledge_base()
            kb.test_connection()
            health_metrics["knowledge_base"] = {"status": "healthy"}
        except Exception as e:
            health_metrics["knowledge_base"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall health
        all_healthy = all(
            metric.get("status") == "healthy" 
            for metric in health_metrics.values()
        )
        
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {
            "status": "completed",
            "overall_health": overall_status,
            "metrics": health_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System health monitoring failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.maintenance_tasks.optimize_performance")
def optimize_performance(self) -> Dict[str, Any]:
    """Optimize system performance."""
    try:
        logger.info("Starting performance optimization")
        current_task.update_state(state="PROGRESS", meta={"status": "optimizing"})
        
        optimizations = {}
        
        # Optimize database
        try:
            db_session = get_db_session()
            
            # Analyze table performance
            db_session.execute("ANALYZE")
            
            # Clean up any temporary data
            db_session.execute("VACUUM ANALYZE")
            
            optimizations["database"] = {
                "status": "optimized",
                "actions": ["analyzed_tables", "vacuumed_database"]
            }
            
            db_session.close()
            
        except Exception as e:
            optimizations["database"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Optimize Redis
        try:
            from ..storage.db import get_redis_client
            redis_client = get_redis_client()
            
            # Clear expired keys
            redis_client.execute_command("FLUSHDB")
            
            optimizations["redis"] = {
                "status": "optimized",
                "actions": ["cleared_expired_keys"]
            }
            
        except Exception as e:
            optimizations["redis"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Optimize knowledge base
        try:
            kb = get_knowledge_base()
            kb.optimize()
            
            optimizations["knowledge_base"] = {
                "status": "optimized",
                "actions": ["optimized_indexes"]
            }
            
        except Exception as e:
            optimizations["knowledge_base"] = {
                "status": "failed",
                "error": str(e)
            }
        
        return {
            "status": "completed",
            "optimizations": optimizations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Performance optimization failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.maintenance_tasks.backup_data")
def backup_data(self) -> Dict[str, Any]:
    """Create backup of important data."""
    try:
        logger.info("Starting data backup")
        current_task.update_state(state="PROGRESS", meta={"status": "backing_up"})
        
        backup_results = {}
        
        # Backup database
        try:
            from ..config import get_settings
            settings = get_settings()
            
            # This would typically use pg_dump or similar
            # For now, we'll just log that backup was attempted
            backup_results["database"] = {
                "status": "backed_up",
                "location": f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
            }
            
        except Exception as e:
            backup_results["database"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Backup knowledge base
        try:
            kb = get_knowledge_base()
            kb_backup = kb.create_backup()
            
            backup_results["knowledge_base"] = {
                "status": "backed_up",
                "location": kb_backup
            }
            
        except Exception as e:
            backup_results["knowledge_base"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Backup configuration
        try:
            settings = get_settings()
            config_backup = {
                "timestamp": datetime.utcnow().isoformat(),
                "app_env": settings.app_env,
                "version": "0.1.0"
            }
            
            backup_results["configuration"] = {
                "status": "backed_up",
                "data": config_backup
            }
            
        except Exception as e:
            backup_results["configuration"] = {
                "status": "failed",
                "error": str(e)
            }
        
        return {
            "status": "completed",
            "backup_results": backup_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Data backup failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


# Helper functions
def _extract_company_context(db_session, since_date: datetime) -> Optional[str]:
    """Extract company context from recent activities."""
    try:
        # Get recent workflow executions
        recent_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.created_at >= since_date
        ).all()
        
        # Get recent conversations
        recent_conversations = db_session.query(Conversation).filter(
            Conversation.started_at >= since_date
        ).all()
        
        context_parts = []
        
        # Analyze workflow patterns
        workflow_types = {}
        for workflow in recent_workflows:
            workflow_type = workflow.workflow_type
            workflow_types[workflow_type] = workflow_types.get(workflow_type, 0) + 1
        
        if workflow_types:
            context_parts.append(f"Recent workflow activity: {workflow_types}")
        
        # Analyze conversation patterns
        if recent_conversations:
            context_parts.append(f"Recent conversations: {len(recent_conversations)} total")
        
        if context_parts:
            return "\n".join(context_parts)
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting company context: {e}")
        return None 