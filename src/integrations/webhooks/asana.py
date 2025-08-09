"""Asana webhook handler for Reflex Executive Assistant."""

import logging
import hmac
import hashlib
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse

from ...config import get_settings
from ...storage.models import AsanaEvent, Task, Project, User
from ...storage.db import get_db_session
from ...workflows.router import route_asana_event
from ...integrations.asana_client import get_asana_client
from ...auth.dependencies import verify_asana_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/events")
async def handle_asana_events(
    request: Request,
    db_session = Depends(get_db_session),
    x_hook_signature: Optional[str] = Header(None),
    x_hook_signature_256: Optional[str] = Header(None)
):
    """Handle Asana webhook events."""
    try:
        # Verify Asana webhook signature
        await verify_asana_webhook(request)
        
        # Parse the webhook payload
        payload = await request.json()
        webhook_id = payload.get("webhook", {}).get("gid")
        events = payload.get("events", [])
        
        logger.info(f"Received Asana webhook {webhook_id} with {len(events)} events")
        
        # Store webhook event in database
        asana_event = AsanaEvent(
            webhook_id=webhook_id,
            webhook_payload=payload,
            event_count=len(events),
            processed=False
        )
        db_session.add(asana_event)
        db_session.commit()
        
        # Process each event
        for event in events:
            await process_asana_event(event, webhook_id, db_session)
        
        asana_event.processed = True
        db_session.commit()
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Asana webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_asana_event(event: Dict[str, Any], webhook_id: str, db_session) -> None:
    """Process an individual Asana event."""
    try:
        event_type = event.get("action")
        resource_type = event.get("resource", {}).get("resource_type")
        resource_id = event.get("resource", {}).get("gid")
        user_id = event.get("user", {}).get("gid")
        
        logger.info(f"Processing Asana event: {event_type} on {resource_type} {resource_id}")
        
        # Route event to appropriate workflow
        await route_asana_event(event, webhook_id, db_session)
        
        # Handle specific event types
        if event_type == "created":
            await handle_resource_created(event, resource_type, resource_id, user_id, db_session)
        elif event_type == "changed":
            await handle_resource_changed(event, resource_type, resource_id, user_id, db_session)
        elif event_type == "deleted":
            await handle_resource_deleted(event, resource_type, resource_id, user_id, db_session)
        elif event_type == "undeleted":
            await handle_resource_undeleted(event, resource_type, resource_id, user_id, db_session)
        
    except Exception as e:
        logger.error(f"Error processing Asana event: {e}", exc_info=True)


async def handle_resource_created(
    event: Dict[str, Any], 
    resource_type: str, 
    resource_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle resource creation events."""
    try:
        if resource_type == "task":
            await handle_task_created(event, resource_id, user_id, db_session)
        elif resource_type == "project":
            await handle_project_created(event, resource_id, user_id, db_session)
        elif resource_type == "story":
            await handle_story_created(event, resource_id, user_id, db_session)
        elif resource_type == "comment":
            await handle_comment_created(event, resource_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling resource creation: {e}", exc_info=True)


async def handle_resource_changed(
    event: Dict[str, Any], 
    resource_type: str, 
    resource_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle resource change events."""
    try:
        if resource_type == "task":
            await handle_task_changed(event, resource_id, user_id, db_session)
        elif resource_type == "project":
            await handle_project_changed(event, resource_id, user_id, db_session)
        elif resource_type == "story":
            await handle_story_changed(event, resource_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling resource change: {e}", exc_info=True)


async def handle_resource_deleted(
    event: Dict[str, Any], 
    resource_type: str, 
    resource_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle resource deletion events."""
    try:
        if resource_type == "task":
            await handle_task_deleted(event, resource_id, user_id, db_session)
        elif resource_type == "project":
            await handle_project_deleted(event, resource_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling resource deletion: {e}", exc_info=True)


async def handle_resource_undeleted(
    event: Dict[str, Any], 
    resource_type: str, 
    resource_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle resource undeletion events."""
    try:
        if resource_type == "task":
            await handle_task_undeleted(event, resource_id, user_id, db_session)
        elif resource_type == "project":
            await handle_project_undeleted(event, resource_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling resource undeletion: {e}", exc_info=True)


async def handle_task_created(
    event: Dict[str, Any], 
    task_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle task creation events."""
    try:
        # Get task details from Asana
        asana_client = get_asana_client()
        task_data = await asana_client.get_task(task_id)
        
        if not task_data:
            logger.warning(f"Could not retrieve task {task_id} from Asana")
            return
        
        # Check if task already exists in database
        existing_task = db_session.query(Task).filter(
            Task.asana_task_id == task_id
        ).first()
        
        if existing_task:
            logger.debug(f"Task {task_id} already exists in database")
            return
        
        # Create task in database
        task = Task(
            asana_task_id=task_id,
            name=task_data.get("name", ""),
            description=task_data.get("notes", ""),
            status=task_data.get("completed", False),
            due_date=task_data.get("due_on"),
            assignee_id=task_data.get("assignee", {}).get("gid"),
            project_id=task_data.get("projects", [{}])[0].get("gid") if task_data.get("projects") else None,
            created_by=user_id,
            task_data=task_data
        )
        db_session.add(task)
        db_session.commit()
        
        logger.info(f"Created task {task_id}: {task.name}")
        
        # Check if this is a high-priority task that needs immediate attention
        if is_high_priority_task(task_data):
            await handle_high_priority_task(task, db_session)
            
    except Exception as e:
        logger.error(f"Error handling task creation: {e}", exc_info=True)


async def handle_task_changed(
    event: Dict[str, Any], 
    task_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle task change events."""
    try:
        # Get updated task details from Asana
        asana_client = get_asana_client()
        task_data = await asana_client.get_task(task_id)
        
        if not task_data:
            logger.warning(f"Could not retrieve updated task {task_id} from Asana")
            return
        
        # Update task in database
        existing_task = db_session.query(Task).filter(
            Task.asana_task_id == task_id
        ).first()
        
        if existing_task:
            existing_task.name = task_data.get("name", existing_task.name)
            existing_task.description = task_data.get("notes", existing_task.description)
            existing_task.status = task_data.get("completed", existing_task.status)
            existing_task.due_date = task_data.get("due_on")
            existing_task.assignee_id = task_data.get("assignee", {}).get("gid")
            existing_task.task_data = task_data
            db_session.commit()
            
            logger.info(f"Updated task {task_id}: {existing_task.name}")
            
            # Check for important changes that need notifications
            await check_task_changes_for_notifications(existing_task, event, db_session)
            
    except Exception as e:
        logger.error(f"Error handling task change: {e}", exc_info=True)


async def handle_task_deleted(
    event: Dict[str, Any], 
    task_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle task deletion events."""
    try:
        # Mark task as deleted in database
        existing_task = db_session.query(Task).filter(
            Task.asana_task_id == task_id
        ).first()
        
        if existing_task:
            existing_task.deleted = True
            existing_task.deleted_at = event.get("created_at")
            existing_task.deleted_by = user_id
            db_session.commit()
            
            logger.info(f"Marked task {task_id} as deleted")
            
    except Exception as e:
        logger.error(f"Error handling task deletion: {e}", exc_info=True)


async def handle_task_undeleted(
    event: Dict[str, Any], 
    task_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle task undeletion events."""
    try:
        # Mark task as not deleted in database
        existing_task = db_session.query(Task).filter(
            Task.asana_task_id == task_id
        ).first()
        
        if existing_task:
            existing_task.deleted = False
            existing_task.deleted_at = None
            existing_task.deleted_by = None
            db_session.commit()
            
            logger.info(f"Marked task {task_id} as not deleted")
            
    except Exception as e:
        logger.error(f"Error handling task undeletion: {e}", exc_info=True)


async def handle_project_created(
    event: Dict[str, Any], 
    project_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle project creation events."""
    try:
        # Get project details from Asana
        asana_client = get_asana_client()
        project_data = await asana_client.get_project(project_id)
        
        if not project_data:
            logger.warning(f"Could not retrieve project {project_id} from Asana")
            return
        
        # Check if project already exists in database
        existing_project = db_session.query(Project).filter(
            Project.asana_project_id == project_id
        ).first()
        
        if existing_project:
            logger.debug(f"Project {project_id} already exists in database")
            return
        
        # Create project in database
        project = Project(
            asana_project_id=project_id,
            name=project_data.get("name", ""),
            description=project_data.get("notes", ""),
            status=project_data.get("archived", False),
            workspace_id=project_data.get("workspace", {}).get("gid"),
            created_by=user_id,
            project_data=project_data
        )
        db_session.add(project)
        db_session.commit()
        
        logger.info(f"Created project {project_id}: {project.name}")
        
    except Exception as e:
        logger.error(f"Error handling project creation: {e}", exc_info=True)


async def handle_project_changed(
    event: Dict[str, Any], 
    project_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle project change events."""
    try:
        # Get updated project details from Asana
        asana_client = get_asana_client()
        project_data = await asana_client.get_project(project_id)
        
        if not project_data:
            logger.warning(f"Could not retrieve updated project {project_id} from Asana")
            return
        
        # Update project in database
        existing_project = db_session.query(Project).filter(
            Project.asana_project_id == project_id
        ).first()
        
        if existing_project:
            existing_project.name = project_data.get("name", existing_project.name)
            existing_project.description = project_data.get("notes", existing_project.description)
            existing_project.status = project_data.get("archived", existing_project.status)
            existing_project.project_data = project_data
            db_session.commit()
            
            logger.info(f"Updated project {project_id}: {existing_project.name}")
            
    except Exception as e:
        logger.error(f"Error handling project change: {e}", exc_info=True)


async def handle_project_deleted(
    event: Dict[str, Any], 
    project_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle project deletion events."""
    try:
        # Mark project as deleted in database
        existing_project = db_session.query(Project).filter(
            Project.asana_project_id == project_id
        ).first()
        
        if existing_project:
            existing_project.deleted = True
            existing_project.deleted_at = event.get("created_at")
            existing_project.deleted_by = user_id
            db_session.commit()
            
            logger.info(f"Marked project {project_id} as deleted")
            
    except Exception as e:
        logger.error(f"Error handling project deletion: {e}", exc_info=True)


async def handle_project_undeleted(
    event: Dict[str, Any], 
    project_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle project undeletion events."""
    try:
        # Mark project as not deleted in database
        existing_project = db_session.query(Project).filter(
            Project.asana_project_id == project_id
        ).first()
        
        if existing_project:
            existing_project.deleted = False
            existing_project.deleted_at = None
            existing_project.deleted_by = None
            db_session.commit()
            
            logger.info(f"Marked project {project_id} as not deleted")
            
    except Exception as e:
        logger.error(f"Error handling project undeletion: {e}", exc_info=True)


async def handle_story_created(
    event: Dict[str, Any], 
    story_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle story creation events (comments, status changes, etc.)."""
    try:
        # Get story details from Asana
        asana_client = get_asana_client()
        story_data = await asana_client.get_story(story_id)
        
        if not story_data:
            logger.warning(f"Could not retrieve story {story_id} from Asana")
            return
        
        story_type = story_data.get("resource_type")
        resource_id = story_data.get("resource", {}).get("gid")
        
        logger.info(f"Created story {story_id} of type {story_type} for resource {resource_id}")
        
        # Handle different story types
        if story_type == "task":
            await handle_task_story(story_data, resource_id, db_session)
        elif story_type == "project":
            await handle_project_story(story_data, resource_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling story creation: {e}", exc_info=True)


async def handle_story_changed(
    event: Dict[str, Any], 
    story_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle story change events."""
    try:
        # Get updated story details from Asana
        asana_client = get_asana_client()
        story_data = await asana_client.get_story(story_id)
        
        if not story_data:
            logger.warning(f"Could not retrieve updated story {story_id} from Asana")
            return
        
        logger.info(f"Updated story {story_id}")
        
    except Exception as e:
        logger.error(f"Error handling story change: {e}", exc_info=True)


async def handle_comment_created(
    event: Dict[str, Any], 
    comment_id: str, 
    user_id: str, 
    db_session
) -> None:
    """Handle comment creation events."""
    try:
        # Get comment details from Asana
        asana_client = get_asana_client()
        comment_data = await asana_client.get_comment(comment_id)
        
        if not comment_data:
            logger.warning(f"Could not retrieve comment {comment_id} from Asana")
            return
        
        logger.info(f"Created comment {comment_id}")
        
        # Check if comment mentions specific users or contains keywords
        await check_comment_for_mentions(comment_data, db_session)
        
    except Exception as e:
        logger.error(f"Error handling comment creation: {e}", exc_info=True)


async def handle_task_story(story_data: Dict[str, Any], task_id: str, db_session) -> None:
    """Handle task-related stories."""
    try:
        story_type = story_data.get("resource_subtype")
        
        if story_type == "comment_added":
            # Handle new comment on task
            await handle_task_comment(story_data, task_id, db_session)
        elif story_type == "assigned":
            # Handle task assignment
            await handle_task_assignment(story_data, task_id, db_session)
        elif story_type == "due_date_changed":
            # Handle due date change
            await handle_task_due_date_change(story_data, task_id, db_session)
        elif story_type == "completed":
            # Handle task completion
            await handle_task_completion(story_data, task_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling task story: {e}", exc_info=True)


async def handle_project_story(story_data: Dict[str, Any], project_id: str, db_session) -> None:
    """Handle project-related stories."""
    try:
        story_type = story_data.get("resource_subtype")
        
        if story_type == "comment_added":
            # Handle new comment on project
            await handle_project_comment(story_data, project_id, db_session)
        elif story_type == "archived":
            # Handle project archival
            await handle_project_archival(story_data, project_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling project story: {e}", exc_info=True)


async def handle_task_comment(story_data: Dict[str, Any], task_id: str, db_session) -> None:
    """Handle task comment stories."""
    try:
        comment_text = story_data.get("text", "")
        user_id = story_data.get("created_by", {}).get("gid")
        
        logger.info(f"New comment on task {task_id} by user {user_id}")
        
        # Check for mentions or keywords that need attention
        await check_comment_for_mentions({"text": comment_text, "created_by": {"gid": user_id}}, db_session)
        
    except Exception as e:
        logger.error(f"Error handling task comment: {e}", exc_info=True)


async def handle_task_assignment(story_data: Dict[str, Any], task_id: str, db_session) -> None:
    """Handle task assignment stories."""
    try:
        assignee_id = story_data.get("new_value", {}).get("gid")
        
        if assignee_id:
            logger.info(f"Task {task_id} assigned to user {assignee_id}")
            
            # TODO: Send notification to assignee
            # await send_task_assignment_notification(task_id, assignee_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling task assignment: {e}", exc_info=True)


async def handle_task_due_date_change(story_data: Dict[str, Any], task_id: str, db_session) -> None:
    """Handle task due date change stories."""
    try:
        new_due_date = story_data.get("new_value")
        old_due_date = story_data.get("old_value")
        
        logger.info(f"Task {task_id} due date changed from {old_due_date} to {new_due_date}")
        
        # Check if this is a critical change
        if is_critical_due_date_change(old_due_date, new_due_date):
            await handle_critical_due_date_change(task_id, old_due_date, new_due_date, db_session)
            
    except Exception as e:
        logger.error(f"Error handling task due date change: {e}", exc_info=True)


async def handle_task_completion(story_data: Dict[str, Any], task_id: str, db_session) -> None:
    """Handle task completion stories."""
    try:
        completed = story_data.get("new_value", False)
        
        if completed:
            logger.info(f"Task {task_id} marked as completed")
            
            # TODO: Handle task completion workflow
            # await handle_task_completion_workflow(task_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling task completion: {e}", exc_info=True)


async def handle_project_comment(story_data: Dict[str, Any], project_id: str, db_session) -> None:
    """Handle project comment stories."""
    try:
        comment_text = story_data.get("text", "")
        user_id = story_data.get("created_by", {}).get("gid")
        
        logger.info(f"New comment on project {project_id} by user {user_id}")
        
        # Check for mentions or keywords that need attention
        await check_comment_for_mentions({"text": comment_text, "created_by": {"gid": user_id}}, db_session)
        
    except Exception as e:
        logger.error(f"Error handling project comment: {e}", exc_info=True)


async def handle_project_archival(story_data: Dict[str, Any], project_id: str, db_session) -> None:
    """Handle project archival stories."""
    try:
        archived = story_data.get("new_value", False)
        
        if archived:
            logger.info(f"Project {project_id} archived")
            
            # TODO: Handle project archival workflow
            # await handle_project_archival_workflow(project_id, db_session)
            
    except Exception as e:
        logger.error(f"Error handling project archival: {e}", exc_info=True)


def is_high_priority_task(task_data: Dict[str, Any]) -> bool:
    """Check if a task is high priority."""
    # Check for priority indicators
    priority = task_data.get("custom_fields", [])
    for field in priority:
        if field.get("name", "").lower() in ["priority", "importance"]:
            value = field.get("display_value", "").lower()
            if value in ["high", "urgent", "critical"]:
                return True
    
    # Check for urgent keywords in name or description
    urgent_keywords = ["urgent", "asap", "critical", "emergency", "immediate"]
    text = f"{task_data.get('name', '')} {task_data.get('notes', '')}".lower()
    
    return any(keyword in text for keyword in urgent_keywords)


def is_critical_due_date_change(old_date: str, new_date: str) -> bool:
    """Check if a due date change is critical."""
    # TODO: Implement logic to determine if due date change is critical
    # This could check if the new date is much sooner than expected
    # or if it's approaching a deadline
    return False


async def handle_high_priority_task(task: Task, db_session) -> None:
    """Handle high priority tasks."""
    try:
        logger.info(f"High priority task detected: {task.name}")
        
        # TODO: Implement high priority task handling
        # This could include:
        # - Sending immediate notifications
        # - Creating follow-up tasks
        # - Escalating to managers
        
    except Exception as e:
        logger.error(f"Error handling high priority task: {e}", exc_info=True)


async def handle_critical_due_date_change(
    task_id: str, 
    old_date: str, 
    new_date: str, 
    db_session
) -> None:
    """Handle critical due date changes."""
    try:
        logger.info(f"Critical due date change for task {task_id}")
        
        # TODO: Implement critical due date change handling
        # This could include:
        # - Sending urgent notifications
        # - Re-prioritizing tasks
        # - Alerting stakeholders
        
    except Exception as e:
        logger.error(f"Error handling critical due date change: {e}", exc_info=True)


async def check_task_changes_for_notifications(
    task: Task, 
    event: Dict[str, Any], 
    db_session
) -> None:
    """Check if task changes need notifications."""
    try:
        # TODO: Implement notification logic for task changes
        # This could check for:
        # - Status changes
        # - Due date changes
        # - Assignment changes
        # - Priority changes
        
        pass
        
    except Exception as e:
        logger.error(f"Error checking task changes for notifications: {e}", exc_info=True)


async def check_comment_for_mentions(comment_data: Dict[str, Any], db_session) -> None:
    """Check if a comment contains mentions or keywords that need attention."""
    try:
        comment_text = comment_data.get("text", "")
        user_id = comment_data.get("created_by", {}).get("gid")
        
        # Check for @mentions
        if "@" in comment_text:
            # TODO: Extract mentioned users and notify them
            pass
        
        # Check for urgent keywords
        urgent_keywords = ["urgent", "asap", "help", "blocked", "issue"]
        if any(keyword in comment_text.lower() for keyword in urgent_keywords):
            # TODO: Flag comment for immediate attention
            pass
            
    except Exception as e:
        logger.error(f"Error checking comment for mentions: {e}", exc_info=True)


@router.get("/health")
async def asana_webhook_health():
    """Health check endpoint for Asana webhooks."""
    return {"status": "healthy", "service": "asana-webhooks"} 