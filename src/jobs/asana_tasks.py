"""Asana background tasks for Reflex Executive Assistant."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import current_task

from ..config import get_settings
from ..integrations.asana_client import get_asana_client
from ..storage.db import get_db_session
from ..storage.models import AsanaTask, AsanaProject, AsanaStory, WorkflowExecution
from ..ai.chain import get_ai_chain
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.sync_asana")
def sync_asana(self) -> Dict[str, Any]:
    """Sync Asana projects, tasks, and stories."""
    try:
        logger.info("Starting Asana synchronization")
        current_task.update_state(state="PROGRESS", meta={"status": "syncing"})
        
        asana_client = get_asana_client()
        db_session = get_db_session()
        
        # Sync projects
        projects = asana_client.get_projects()
        project_count = 0
        for project_data in projects:
            try:
                project = _sync_project(project_data, db_session)
                if project:
                    project_count += 1
            except Exception as e:
                logger.error(f"Error syncing project {project_data.get('gid')}: {e}")
                continue
        
        # Sync tasks from active projects
        task_count = 0
        active_projects = db_session.query(AsanaProject).filter(
            AsanaProject.archived == False
        ).all()
        
        for project in active_projects:
            try:
                tasks = asana_client.get_project_tasks(project.asana_id)
                for task_data in tasks:
                    if _should_process_task(task_data):
                        task = _sync_task(task_data, project.asana_id, db_session)
                        if task:
                            task_count += 1
                            
                            # Process with AI if it's important or needs attention
                            if _is_important_task(task_data):
                                _process_task_ai(task, task_data)
            except Exception as e:
                logger.error(f"Error syncing tasks for project {project.asana_id}: {e}")
                continue
        
        # Sync stories (comments and updates)
        story_count = 0
        active_tasks = db_session.query(AsanaTask).filter(
            AsanaTask.completed == False
        ).all()
        
        for task in active_tasks:
            try:
                stories = asana_client.get_task_stories(task.asana_id)
                for story_data in stories:
                    if _should_process_story(story_data):
                        story = _sync_story(story_data, task.asana_id, db_session)
                        if story:
                            story_count += 1
                            
                            # Process important updates with AI
                            if _is_important_story(story_data):
                                _process_story_ai(story, story_data)
            except Exception as e:
                logger.error(f"Error syncing stories for task {task.asana_id}: {e}")
                continue
        
        db_session.close()
        
        result = {
            "status": "completed",
            "projects_synced": project_count,
            "tasks_synced": task_count,
            "stories_synced": story_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Asana sync completed: {project_count} projects, {task_count} tasks, {story_count} stories")
        return result
        
    except Exception as e:
        logger.error(f"Asana sync failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.process_task")
def process_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
    """Process a specific Asana task with AI."""
    try:
        logger.info(f"Processing Asana task {task_id} for user {user_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "processing"})
        
        db_session = get_db_session()
        
        # Get task
        task = db_session.query(AsanaTask).filter(AsanaTask.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="asana_task",
            trigger_user=user_id,
            trigger_content=f"Task: {task.name}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Process with AI
        ai_chain = get_ai_chain()
        result = ai_chain.process_asana_update(
            event_data={
                "action": "task_analysis",
                "task_id": task.asana_id,
                "task_name": task.name,
                "task_description": task.description,
                "task_status": task.status,
                "task_due_date": task.due_date.isoformat() if task.due_date else None,
                "project_id": task.project_id
            },
            user_id=user_id,
            workflow_id=workflow_exec.id
        )
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = result
        db_session.commit()
        
        db_session.close()
        
        return {
            "status": "completed",
            "task_id": task_id,
            "workflow_id": workflow_exec.id,
            "ai_result": result
        }
        
    except Exception as e:
        logger.error(f"Asana task processing failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.create_task")
def create_task(self, project_id: str, task_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a new Asana task in the background."""
    try:
        logger.info(f"Creating Asana task in project {project_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "creating"})
        
        asana_client = get_asana_client()
        
        # Create task in Asana
        result = asana_client.create_task(task_data)
        
        if result:
            # Store in database
            db_session = get_db_session()
            
            task = AsanaTask(
                asana_id=result.get("gid"),
                name=task_data.get("name", "Untitled Task"),
                description=task_data.get("description", ""),
                status=task_data.get("status", "incomplete"),
                project_id=project_id,
                assignee_id=task_data.get("assignee"),
                due_date=datetime.fromisoformat(task_data.get("due_date")) if task_data.get("due_date") else None,
                priority=task_data.get("priority", "medium"),
                completed=task_data.get("completed", False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=result
            )
            db_session.add(task)
            db_session.commit()
            db_session.close()
            
            return {
                "status": "created",
                "task_id": task.id,
                "asana_id": result.get("gid"),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise Exception("Failed to create task in Asana")
        
    except Exception as e:
        logger.error(f"Asana task creation failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.update_task")
def update_task(self, task_id: str, updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Update an existing Asana task."""
    try:
        logger.info(f"Updating Asana task {task_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "updating"})
        
        asana_client = get_asana_client()
        db_session = get_db_session()
        
        # Get task from database
        task = db_session.query(AsanaTask).filter(AsanaTask.asana_id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found in database")
        
        # Update task in Asana
        result = asana_client.update_task(task_id, updates)
        
        if result:
            # Update local database
            if "name" in updates:
                task.name = updates["name"]
            if "description" in updates:
                task.description = updates["description"]
            if "status" in updates:
                task.status = updates["status"]
            if "assignee" in updates:
                task.assignee_id = updates["assignee"]
            if "due_date" in updates:
                task.due_date = datetime.fromisoformat(updates["due_date"]) if updates["due_date"] else None
            if "priority" in updates:
                task.priority = updates["priority"]
            if "completed" in updates:
                task.completed = updates["completed"]
            
            task.updated_at = datetime.utcnow()
            task.metadata = result
            db_session.commit()
            
            # Process with AI if significant changes
            if _has_significant_changes(updates):
                _process_task_ai(task, {"action": "update", **updates})
            
            db_session.close()
            
            return {
                "status": "updated",
                "task_id": task.id,
                "asana_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise Exception("Failed to update task in Asana")
        
    except Exception as e:
        logger.error(f"Asana task update failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.monitor_deadlines")
def monitor_deadlines(self) -> Dict[str, Any]:
    """Monitor tasks approaching deadlines and send notifications."""
    try:
        logger.info("Starting deadline monitoring")
        current_task.update_state(state="PROGRESS", meta={"status": "monitoring"})
        
        db_session = get_db_session()
        
        # Find tasks approaching deadlines
        now = datetime.utcnow()
        warning_threshold = now + timedelta(days=3)  # 3 days warning
        urgent_threshold = now + timedelta(days=1)   # 1 day urgent
        
        approaching_deadlines = db_session.query(AsanaTask).filter(
            AsanaTask.completed == False,
            AsanaTask.due_date.isnot(None),
            AsanaTask.due_date <= warning_threshold
        ).all()
        
        urgent_tasks = []
        warning_tasks = []
        
        for task in approaching_deadlines:
            if task.due_date <= urgent_threshold:
                urgent_tasks.append(task)
            else:
                warning_tasks.append(task)
        
        # Process urgent tasks with AI
        processed_count = 0
        for task in urgent_tasks:
            try:
                _process_task_ai(task, {"action": "deadline_urgent", "days_remaining": (task.due_date - now).days})
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing urgent task {task.id}: {e}")
                continue
        
        db_session.close()
        
        return {
            "status": "completed",
            "urgent_tasks": len(urgent_tasks),
            "warning_tasks": len(warning_tasks),
            "processed_count": processed_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Deadline monitoring failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.analyze_project_health")
def analyze_project_health(self, project_id: str) -> Dict[str, Any]:
    """Analyze project health and provide insights."""
    try:
        logger.info(f"Analyzing project health for {project_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "analyzing"})
        
        db_session = get_db_session()
        
        # Get project and tasks
        project = db_session.query(AsanaProject).filter(AsanaProject.asana_id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        tasks = db_session.query(AsanaTask).filter(AsanaTask.project_id == project.asana_id).all()
        
        # Calculate metrics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.completed])
        overdue_tasks = len([t for t in tasks if t.due_date and t.due_date < datetime.utcnow() and not t.completed])
        high_priority_tasks = len([t for t in tasks if t.priority == "high" and not t.completed])
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Analyze with AI
        ai_chain = get_ai_chain()
        analysis = ai_chain.process_asana_update(
            event_data={
                "action": "project_health_analysis",
                "project_id": project_id,
                "project_name": project.name,
                "metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "overdue_tasks": overdue_tasks,
                    "high_priority_tasks": high_priority_tasks,
                    "completion_rate": completion_rate
                }
            },
            user_id="system"
        )
        
        db_session.close()
        
        return {
            "status": "completed",
            "project_id": project_id,
            "metrics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "overdue_tasks": overdue_tasks,
                "high_priority_tasks": high_priority_tasks,
                "completion_rate": completion_rate
            },
            "ai_analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Project health analysis failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.asana_tasks.cleanup_completed_tasks")
def cleanup_completed_tasks(self, days_old: int = 30) -> Dict[str, Any]:
    """Clean up old completed tasks from the database."""
    try:
        logger.info(f"Cleaning up completed tasks older than {days_old} days")
        current_task.update_state(state="PROGRESS", meta={"status": "cleaning"})
        
        db_session = get_db_session()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count tasks to be deleted
        old_tasks_count = db_session.query(AsanaTask).filter(
            AsanaTask.completed == True,
            AsanaTask.updated_at < cutoff_date
        ).count()
        
        # Delete old completed tasks
        deleted_count = db_session.query(AsanaTask).filter(
            AsanaTask.completed == True,
            AsanaTask.updated_at < cutoff_date
        ).delete()
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "old_tasks_count": old_tasks_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Task cleanup failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


# Helper functions
def _sync_project(project_data: Dict[str, Any], db_session) -> Optional[AsanaProject]:
    """Sync an Asana project to the database."""
    try:
        # Check if project exists
        existing = db_session.query(AsanaProject).filter(
            AsanaProject.asana_id == project_data.get("gid")
        ).first()
        
        if existing:
            # Update existing project
            existing.name = project_data.get("name", existing.name)
            existing.description = project_data.get("description", existing.description)
            existing.status = project_data.get("status", existing.status)
            existing.archived = project_data.get("archived", existing.archived)
            existing.team_id = project_data.get("team", {}).get("gid", existing.team_id)
            existing.workspace_id = project_data.get("workspace", {}).get("gid", existing.workspace_id)
            existing.updated_at = datetime.utcnow()
            existing.metadata = project_data
            
            return existing
        else:
            # Create new project
            project = AsanaProject(
                asana_id=project_data.get("gid"),
                name=project_data.get("name", "Untitled Project"),
                description=project_data.get("description", ""),
                status=project_data.get("status", "active"),
                archived=project_data.get("archived", False),
                team_id=project_data.get("team", {}).get("gid"),
                workspace_id=project_data.get("workspace", {}).get("gid"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=project_data
            )
            
            db_session.add(project)
            db_session.commit()
            return project
            
    except Exception as e:
        logger.error(f"Error syncing project: {e}")
        db_session.rollback()
        return None


def _sync_task(task_data: Dict[str, Any], project_id: str, db_session) -> Optional[AsanaTask]:
    """Sync an Asana task to the database."""
    try:
        # Check if task exists
        existing = db_session.query(AsanaTask).filter(
            AsanaTask.asana_id == task_data.get("gid")
        ).first()
        
        if existing:
            # Update existing task
            existing.name = task_data.get("name", existing.name)
            existing.description = task_data.get("description", existing.description)
            existing.status = task_data.get("status", existing.status)
            existing.assignee_id = task_data.get("assignee", {}).get("gid", existing.assignee_id)
            existing.due_date = datetime.fromisoformat(task_data.get("due_date")) if task_data.get("due_date") else None
            existing.priority = task_data.get("priority", existing.priority)
            existing.completed = task_data.get("completed", existing.completed)
            existing.updated_at = datetime.utcnow()
            existing.metadata = task_data
            
            return existing
        else:
            # Create new task
            task = AsanaTask(
                asana_id=task_data.get("gid"),
                name=task_data.get("name", "Untitled Task"),
                description=task_data.get("description", ""),
                status=task_data.get("status", "incomplete"),
                project_id=project_id,
                assignee_id=task_data.get("assignee", {}).get("gid"),
                due_date=datetime.fromisoformat(task_data.get("due_date")) if task_data.get("due_date") else None,
                priority=task_data.get("priority", "medium"),
                completed=task_data.get("completed", False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=task_data
            )
            
            db_session.add(task)
            db_session.commit()
            return task
            
    except Exception as e:
        logger.error(f"Error syncing task: {e}")
        db_session.rollback()
        return None


def _sync_story(story_data: Dict[str, Any], task_id: str, db_session) -> Optional[AsanaStory]:
    """Sync an Asana story to the database."""
    try:
        # Check if story exists
        existing = db_session.query(AsanaStory).filter(
            AsanaStory.asana_id == story_data.get("gid")
        ).first()
        
        if existing:
            return existing
        
        # Create new story
        story = AsanaStory(
            asana_id=story_data.get("gid"),
            task_id=task_id,
            type=story_data.get("resource_type", "comment"),
            text=story_data.get("text", ""),
            created_by=story_data.get("created_by", {}).get("gid"),
            created_at=datetime.fromisoformat(story_data.get("created_at")) if story_data.get("created_at") else datetime.utcnow(),
            metadata=story_data
        )
        
        db_session.add(story)
        db_session.commit()
        return story
        
    except Exception as e:
        logger.error(f"Error syncing story: {e}")
        db_session.rollback()
        return None


def _should_process_task(task_data: Dict[str, Any]) -> bool:
    """Determine if a task should be processed."""
    # Skip completed tasks
    if task_data.get("completed"):
        return False
    
    # Skip tasks with minimal content
    name = task_data.get("name", "")
    if len(name.strip()) < 5:
        return False
    
    return True


def _should_process_story(story_data: Dict[str, Any]) -> bool:
    """Determine if a story should be processed."""
    # Skip system stories
    if story_data.get("resource_type") in ["system", "automation"]:
        return False
    
    # Skip empty stories
    text = story_data.get("text", "")
    if not text or len(text.strip()) < 5:
        return False
    
    return True


def _is_important_task(task_data: Dict[str, Any]) -> bool:
    """Determine if a task is important and should be processed with AI."""
    # Check priority
    if task_data.get("priority") == "high":
        return True
    
    # Check due date (urgent tasks)
    if task_data.get("due_date"):
        due_date = datetime.fromisoformat(task_data.get("due_date"))
        days_until_due = (due_date - datetime.utcnow()).days
        if days_until_due <= 3:
            return True
    
    # Check for important keywords in name/description
    important_keywords = [
        "urgent", "critical", "blocker", "deadline", "review", "approval",
        "decision", "meeting", "presentation", "report", "analysis"
    ]
    
    text = f"{task_data.get('name', '')} {task_data.get('description', '')}".lower()
    if any(keyword in text for keyword in important_keywords):
        return True
    
    return False


def _is_important_story(story_data: Dict[str, Any]) -> bool:
    """Determine if a story is important and should be processed with AI."""
    text = story_data.get("text", "").lower()
    
    # Check for important keywords
    important_keywords = [
        "urgent", "blocked", "issue", "problem", "help", "question",
        "deadline", "meeting", "call", "review", "approval", "decision"
    ]
    
    if any(keyword in text for keyword in important_keywords):
        return True
    
    # Check for questions
    if "?" in text:
        return True
    
    return False


def _process_task_ai(task: AsanaTask, task_data: Dict[str, Any]) -> None:
    """Process task with AI for analysis."""
    try:
        # Queue AI processing task
        process_task.delay(
            task_id=str(task.id),
            user_id=task.assignee_id or "system"
        )
        
    except Exception as e:
        logger.error(f"Error queuing task AI processing: {e}")


def _process_story_ai(story: AsanaStory, story_data: Dict[str, Any]) -> None:
    """Process story with AI for analysis."""
    try:
        # Queue AI processing task for the parent task
        process_task.delay(
            task_id=str(story.task_id),
            user_id=story.created_by or "system"
        )
        
    except Exception as e:
        logger.error(f"Error queuing story AI processing: {e}")


def _has_significant_changes(updates: Dict[str, Any]) -> bool:
    """Determine if task updates are significant enough for AI processing."""
    significant_fields = ["status", "assignee", "due_date", "priority", "completed"]
    return any(field in updates for field in significant_fields) 