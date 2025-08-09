"""Workflow background tasks for Reflex Executive Assistant."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import current_task

from ..config import get_settings
from ..storage.db import get_db_session
from ..storage.models import WorkflowExecution, Conversation, Message
from ..ai.chain import get_ai_chain
from ..workflows.engine import get_workflow_engine
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.jobs.tasks.workflow_tasks.process_workflow")
def process_workflow(self, workflow_id: str) -> Dict[str, Any]:
    """Process a workflow execution with the AI chain."""
    try:
        logger.info(f"Processing workflow {workflow_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "processing"})
        
        db_session = get_db_session()
        
        # Get workflow execution
        workflow_exec = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.id == workflow_id
        ).first()
        
        if not workflow_exec:
            raise ValueError(f"Workflow execution {workflow_id} not found")
        
        # Update workflow status
        workflow_exec.status = "processing"
        workflow_exec.updated_at = datetime.utcnow()
        db_session.commit()
        
        try:
            # Get AI chain and process based on workflow type
            ai_chain = get_ai_chain()
            
            if workflow_exec.workflow_type == "slack_mention":
                result = ai_chain.process_slack_message(
                    message=workflow_exec.trigger_content,
                    user_id=workflow_exec.trigger_user,
                    channel_id=workflow_exec.trigger_channel,
                    team_id=workflow_exec.team_id,
                    workflow_id=workflow_exec.id
                )
            elif workflow_exec.workflow_type == "email_processing":
                # Parse email content from trigger_content
                email_data = _parse_email_content(workflow_exec.trigger_content)
                result = ai_chain.process_email(
                    email_data=email_data,
                    user_id=workflow_exec.trigger_user,
                    workflow_id=workflow_exec.id
                )
            elif workflow_exec.workflow_type == "asana_task":
                # Parse task data from trigger_content
                task_data = _parse_task_content(workflow_exec.trigger_content)
                result = ai_chain.process_asana_update(
                    event_data=task_data,
                    user_id=workflow_exec.trigger_user,
                    workflow_id=workflow_exec.id
                )
            else:
                # Generic workflow processing
                result = ai_chain.process_generic_workflow(
                    workflow_type=workflow_exec.workflow_type,
                    content=workflow_exec.trigger_content,
                    user_id=workflow_exec.trigger_user,
                    workflow_id=workflow_exec.id
                )
            
            # Update workflow execution with success
            workflow_exec.status = "completed"
            workflow_exec.completed_at = datetime.utcnow()
            workflow_exec.result = result
            workflow_exec.updated_at = datetime.utcnow()
            db_session.commit()
            
            # Store conversation and message
            _store_workflow_conversation(workflow_exec, result, db_session)
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            
            return {
                "status": "completed",
                "workflow_id": workflow_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            # Update workflow execution with failure
            workflow_exec.status = "failed"
            workflow_exec.error_message = str(e)
            workflow_exec.updated_at = datetime.utcnow()
            db_session.commit()
            
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise
            
        finally:
            db_session.close()
        
    except Exception as e:
        logger.error(f"Workflow processing failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.workflow_tasks.monitor_workflows")
def monitor_workflows(self) -> Dict[str, Any]:
    """Monitor active workflows and handle timeouts."""
    try:
        logger.info("Starting workflow monitoring")
        current_task.update_state(state="PROGRESS", meta={"status": "monitoring"})
        
        db_session = get_db_session()
        
        # Find stuck workflows (processing for too long)
        timeout_threshold = datetime.utcnow() - timedelta(minutes=30)
        stuck_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "processing",
            WorkflowExecution.updated_at < timeout_threshold
        ).all()
        
        # Find workflows that have been started but not updated
        stale_threshold = datetime.utcnow() - timedelta(minutes=5)
        stale_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "started",
            Workflow_exec.started_at < stale_threshold
        ).all()
        
        # Handle stuck workflows
        stuck_count = 0
        for workflow in stuck_workflows:
            try:
                workflow.status = "timeout"
                workflow.error_message = "Workflow timed out after 30 minutes"
                workflow.updated_at = datetime.utcnow()
                stuck_count += 1
            except Exception as e:
                logger.error(f"Error handling stuck workflow {workflow.id}: {e}")
                continue
        
        # Handle stale workflows
        stale_count = 0
        for workflow in stale_workflows:
            try:
                # Retry processing
                process_workflow.delay(str(workflow.id))
                stale_count += 1
            except Exception as e:
                logger.error(f"Error retrying stale workflow {workflow.id}: {e}")
                continue
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "stuck_workflows_handled": stuck_count,
            "stale_workflows_retried": stale_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Workflow monitoring failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.workflow_tasks.retry_failed_workflows")
def retry_failed_workflows(self, max_retries: int = 3) -> Dict[str, Any]:
    """Retry failed workflows with exponential backoff."""
    try:
        logger.info("Starting failed workflow retry process")
        current_task.update_state(state="PROGRESS", meta={"status": "retrying"})
        
        db_session = get_db_session()
        
        # Find failed workflows that haven't exceeded max retries
        failed_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "failed",
            WorkflowExecution.retry_count < max_retries
        ).all()
        
        retried_count = 0
        for workflow in failed_workflows:
            try:
                # Calculate backoff delay
                backoff_minutes = 2 ** workflow.retry_count  # Exponential backoff
                
                # Schedule retry with delay
                process_workflow.apply_async(
                    args=[str(workflow.id)],
                    countdown=backoff_minutes * 60  # Convert to seconds
                )
                
                # Update retry count
                workflow.retry_count += 1
                workflow.status = "retrying"
                workflow.updated_at = datetime.utcnow()
                
                retried_count += 1
                
            except Exception as e:
                logger.error(f"Error scheduling retry for workflow {workflow.id}: {e}")
                continue
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "workflows_retried": retried_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed workflow retry failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.workflow_tasks.cleanup_old_workflows")
def cleanup_old_workflows(self, days_old: int = 90) -> Dict[str, Any]:
    """Clean up old completed and failed workflows."""
    try:
        logger.info(f"Cleaning up workflows older than {days_old} days")
        current_task.update_state(state="PROGRESS", meta={"status": "cleaning"})
        
        db_session = get_db_session()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count workflows to be deleted
        old_workflows_count = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.created_at < cutoff_date,
            WorkflowExecution.status.in_(["completed", "failed", "timeout"])
        ).count()
        
        # Delete old workflows
        deleted_count = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.created_at < cutoff_date,
            WorkflowExecution.status.in_(["completed", "failed", "timeout"])
        ).delete()
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "old_workflows_count": old_workflows_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Workflow cleanup failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.workflow_tasks.analyze_workflow_performance")
def analyze_workflow_performance(self) -> Dict[str, Any]:
    """Analyze workflow performance and provide insights."""
    try:
        logger.info("Starting workflow performance analysis")
        current_task.update_state(state="PROGRESS", meta={"status": "analyzing"})
        
        db_session = get_db_session()
        
        # Get workflow statistics for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        total_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.created_at >= thirty_days_ago
        ).count()
        
        completed_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "completed",
            WorkflowExecution.created_at >= thirty_days_ago
        ).count()
        
        failed_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "failed",
            WorkflowExecution.created_at >= thirty_days_ago
        ).count()
        
        timeout_workflows = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "timeout",
            WorkflowExecution.created_at >= thirty_days_ago
        ).count()
        
        # Calculate success rate
        success_rate = (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0
        
        # Get average processing time for completed workflows
        completed_workflows_data = db_session.query(WorkflowExecution).filter(
            WorkflowExecution.status == "completed",
            WorkflowExecution.created_at >= thirty_days_ago,
            WorkflowExecution.completed_at.isnot(None)
        ).all()
        
        total_processing_time = timedelta()
        for workflow in completed_workflows_data:
            if workflow.started_at and workflow.completed_at:
                processing_time = workflow.completed_at - workflow.started_at
                total_processing_time += processing_time
        
        avg_processing_time = total_processing_time / len(completed_workflows_data) if completed_workflows_data else timedelta()
        
        # Get workflow type distribution
        workflow_types = db_session.query(
            WorkflowExecution.workflow_type,
            db_session.func.count(WorkflowExecution.id)
        ).filter(
            WorkflowExecution.created_at >= thirty_days_ago
        ).group_by(WorkflowExecution.workflow_type).all()
        
        type_distribution = {workflow_type: count for workflow_type, count in workflow_types}
        
        # Analyze with AI for insights
        ai_chain = get_ai_chain()
        analysis = ai_chain.process_generic_workflow(
            workflow_type="performance_analysis",
            content=f"Workflow Performance Analysis: {success_rate:.1f}% success rate, {avg_processing_time} avg processing time",
            user_id="system",
            workflow_id=None
        )
        
        db_session.close()
        
        return {
            "status": "completed",
            "metrics": {
                "total_workflows": total_workflows,
                "completed_workflows": completed_workflows,
                "failed_workflows": failed_workflows,
                "timeout_workflows": timeout_workflows,
                "success_rate": success_rate,
                "avg_processing_time": str(avg_processing_time),
                "type_distribution": type_distribution
            },
            "ai_analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Workflow performance analysis failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.workflow_tasks.optimize_workflow_routing")
def optimize_workflow_routing(self) -> Dict[str, Any]:
    """Analyze and optimize workflow routing based on performance data."""
    try:
        logger.info("Starting workflow routing optimization")
        current_task.update_state(state="PROGRESS", meta={"status": "optimizing"})
        
        db_session = get_db_session()
        
        # Get workflow engine for optimization
        workflow_engine = get_workflow_engine()
        
        # Analyze routing patterns
        routing_analysis = _analyze_routing_patterns(db_session)
        
        # Get AI recommendations for optimization
        ai_chain = get_ai_chain()
        optimization_recommendations = ai_chain.process_generic_workflow(
            workflow_type="routing_optimization",
            content=f"Routing Analysis: {routing_analysis}",
            user_id="system",
            workflow_id=None
        )
        
        # Apply optimizations if recommended
        optimizations_applied = 0
        if optimization_recommendations and "routing_optimizations" in optimization_recommendations:
            for optimization in optimization_recommendations["routing_optimizations"]:
                try:
                    # Apply routing optimization
                    workflow_engine.optimize_routing(
                        workflow_type=optimization.get("workflow_type"),
                        new_routing=optimization.get("routing"),
                        reason=optimization.get("reason")
                    )
                    optimizations_applied += 1
                except Exception as e:
                    logger.error(f"Error applying routing optimization: {e}")
                    continue
        
        db_session.close()
        
        return {
            "status": "completed",
            "routing_analysis": routing_analysis,
            "optimization_recommendations": optimization_recommendations,
            "optimizations_applied": optimizations_applied,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Workflow routing optimization failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


# Helper functions
def _parse_email_content(content: str) -> Dict[str, Any]:
    """Parse email content from workflow trigger content."""
    try:
        # Simple parsing - in production, this would be more sophisticated
        lines = content.split('\n')
        subject = ""
        body = ""
        
        for i, line in enumerate(lines):
            if line.startswith("Subject:"):
                subject = line.replace("Subject:", "").strip()
            elif line.startswith("Body:"):
                body = '\n'.join(lines[i+1:])
                break
        
        return {
            "subject": subject,
            "body": body,
            "from": "unknown",
            "to": "unknown"
        }
    except Exception as e:
        logger.error(f"Error parsing email content: {e}")
        return {
            "subject": "Unknown",
            "body": content,
            "from": "unknown",
            "to": "unknown"
        }


def _parse_task_content(content: str) -> Dict[str, Any]:
    """Parse task content from workflow trigger content."""
    try:
        # Simple parsing - in production, this would be more sophisticated
        lines = content.split('\n')
        task_name = ""
        description = ""
        
        for i, line in enumerate(lines):
            if line.startswith("Task:"):
                task_name = line.replace("Task:", "").strip()
            elif line.startswith("Description:"):
                description = '\n'.join(lines[i+1:])
                break
        
        return {
            "action": "task_analysis",
            "task_name": task_name,
            "task_description": description
        }
    except Exception as e:
        logger.error(f"Error parsing task content: {e}")
        return {
            "action": "task_analysis",
            "task_name": "Unknown Task",
            "task_description": content
        }


def _store_workflow_conversation(workflow_exec: WorkflowExecution, result: Dict[str, Any], db_session) -> None:
    """Store workflow conversation and message in the database."""
    try:
        # Create or get conversation
        conversation = db_session.query(Conversation).filter(
            Conversation.workflow_id == workflow_exec.id
        ).first()
        
        if not conversation:
            conversation = Conversation(
                workflow_id=workflow_exec.id,
                user_id=workflow_exec.trigger_user,
                title=f"Workflow: {workflow_exec.workflow_type}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db_session.add(conversation)
            db_session.commit()
        
        # Store the workflow result as a message
        if result and isinstance(result, dict):
            message_content = result.get("response", str(result))
        else:
            message_content = str(result)
        
        message = Message(
            conversation_id=conversation.id,
            content=message_content,
            role="assistant",
            metadata={
                "workflow_id": workflow_exec.id,
                "workflow_type": workflow_exec.workflow_type,
                "result": result
            },
            created_at=datetime.utcnow()
        )
        
        db_session.add(message)
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error storing workflow conversation: {e}")
        db_session.rollback()


def _analyze_routing_patterns(db_session) -> Dict[str, Any]:
    """Analyze workflow routing patterns for optimization."""
    try:
        # Get routing statistics for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Analyze workflow type distribution and success rates
        workflow_stats = db_session.query(
            WorkflowExecution.workflow_type,
            db_session.func.count(WorkflowExecution.id).label('total'),
            db_session.func.avg(
                db_session.case(
                    (WorkflowExecution.status == "completed", 1),
                    else_=0
                )
            ).label('success_rate')
        ).filter(
            WorkflowExecution.created_at >= thirty_days_ago
        ).group_by(WorkflowExecution.workflow_type).all()
        
        routing_analysis = {
            "workflow_types": {},
            "total_workflows": 0,
            "overall_success_rate": 0.0
        }
        
        total_workflows = 0
        total_successful = 0
        
        for stat in workflow_stats:
            workflow_type = stat.workflow_type
            count = stat.total
            success_rate = float(stat.success_rate or 0)
            
            routing_analysis["workflow_types"][workflow_type] = {
                "count": count,
                "success_rate": success_rate
            }
            
            total_workflows += count
            total_successful += int(count * success_rate)
        
        routing_analysis["total_workflows"] = total_workflows
        routing_analysis["overall_success_rate"] = (total_successful / total_workflows * 100) if total_workflows > 0 else 0
        
        return routing_analysis
        
    except Exception as e:
        logger.error(f"Error analyzing routing patterns: {e}")
        return {"error": str(e)} 