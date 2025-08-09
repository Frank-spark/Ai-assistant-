"""Workflow router for Reflex Executive Assistant."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from .engine import get_workflow_engine, WorkflowEngine
from ..storage.models import Workflow, WorkflowExecution, WorkflowStep
from ..auth.dependencies import get_current_user
from ..ai.chain import get_ai_chain
from ..storage.db import get_db_session
from ..storage.models import EventLog
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


# Pydantic models for API requests/responses

class WorkflowCreateRequest(BaseModel):
    """Request model for creating a workflow."""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps configuration")
    triggers: List[str] = Field(..., description="Workflow trigger types")
    is_active: bool = Field(True, description="Whether the workflow is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WorkflowUpdateRequest(BaseModel):
    """Request model for updating a workflow."""
    name: Optional[str] = Field(None, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    steps: Optional[List[Dict[str, Any]]] = Field(None, description="Workflow steps configuration")
    triggers: Optional[List[str]] = Field(None, description="Workflow trigger types")
    is_active: Optional[bool] = Field(None, description="Whether the workflow is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WorkflowExecutionRequest(BaseModel):
    """Request model for executing a workflow."""
    workflow_id: str = Field(..., description="ID of the workflow to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Execution parameters")
    source: str = Field(..., description="Source of the execution request")
    source_id: str = Field(..., description="Source identifier")


class WorkflowResponse(BaseModel):
    """Response model for workflow data."""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    triggers: List[str]
    is_active: bool
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution data."""
    execution_id: str
    workflow_id: str
    user_id: str
    source: str
    source_id: str
    status: str
    parameters: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]


class WorkflowStepResponse(BaseModel):
    """Response model for workflow step data."""
    step_id: str
    execution_id: str
    step_type: str
    status: str
    configuration: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]


# API endpoints

@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: str = Depends(get_current_user),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Create a new workflow."""
    try:
        workflow_id = await workflow_engine.create_workflow(
            name=request.name,
            description=request.description,
            steps=request.steps,
            triggers=request.triggers,
            is_active=request.is_active,
            metadata=request.metadata,
            created_by=current_user
        )
        
        # Get the created workflow
        workflow = workflow_engine.active_workflows.get(workflow_id)
        if not workflow:
            raise HTTPException(status_code=500, detail="Failed to retrieve created workflow")
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            steps=workflow.steps,
            triggers=workflow.triggers,
            is_active=workflow.is_active,
            metadata=workflow.metadata,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """List all workflows."""
    try:
        workflows = list(workflow_engine.active_workflows.values())
        
        return [
            WorkflowResponse(
                id=workflow.id,
                name=workflow.name,
                description=workflow.description,
                steps=workflow.steps,
                triggers=workflow.triggers,
                is_active=workflow.is_active,
                metadata=workflow.metadata,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at
            )
            for workflow in workflows
        ]
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Get a specific workflow by ID."""
    try:
        workflow = workflow_engine.active_workflows.get(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            steps=workflow.steps,
            triggers=workflow.triggers,
            is_active=workflow.is_active,
            metadata=workflow.metadata,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    current_user: str = Depends(get_current_user),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Update an existing workflow."""
    try:
        workflow = workflow_engine.active_workflows.get(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Update workflow fields
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.description is not None:
            update_data['description'] = request.description
        if request.steps is not None:
            update_data['steps'] = request.steps
        if request.triggers is not None:
            update_data['triggers'] = request.triggers
        if request.is_active is not None:
            update_data['is_active'] = request.is_active
        if request.metadata is not None:
            update_data['metadata'] = request.metadata
        
        # Update the workflow
        for key, value in update_data.items():
            setattr(workflow, key, value)
        
        workflow.updated_at = datetime.now()
        workflow.updated_by = current_user
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            steps=workflow.steps,
            triggers=workflow.triggers,
            is_active=workflow.is_active,
            metadata=workflow.metadata,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: str = Depends(get_current_user),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Delete a workflow."""
    try:
        workflow = workflow_engine.active_workflows.get(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Remove from active workflows
        del workflow_engine.active_workflows[workflow_id]
        
        logger.info(f"Workflow {workflow_id} deleted by user {current_user}")
        return {"message": "Workflow deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Execute a workflow."""
    try:
        execution_id = await workflow_engine.execute_workflow(
            workflow_id=request.workflow_id,
            user_id=current_user,
            source=request.source,
            source_id=request.source_id,
            parameters=request.parameters or {}
        )
        
        # Get execution details
        execution = await workflow_engine.get_workflow_status(execution_id)
        if not execution:
            raise HTTPException(status_code=500, detail="Failed to retrieve execution details")
        
        return WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=request.workflow_id,
            user_id=current_user,
            source=request.source,
            source_id=request.source_id,
            status=execution.get('status', 'unknown'),
            parameters=request.parameters or {},
            started_at=datetime.now(),
            completed_at=None,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Get workflow execution status."""
    try:
        execution = await workflow_engine.get_workflow_status(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=execution.get('workflow_id', 'unknown'),
            user_id=execution.get('user_id', 'unknown'),
            source=execution.get('source', 'unknown'),
            source_id=execution.get('source_id', 'unknown'),
            status=execution.get('status', 'unknown'),
            parameters=execution.get('parameters', {}),
            started_at=execution.get('started_at', datetime.now()),
            completed_at=execution.get('completed_at'),
            error=execution.get('error')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/cancel")
async def cancel_workflow_execution(
    execution_id: str,
    current_user: str = Depends(get_current_user),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Cancel a running workflow execution."""
    try:
        success = await workflow_engine.cancel_workflow(execution_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel workflow execution")
        
        logger.info(f"Workflow execution {execution_id} cancelled by user {current_user}")
        return {"message": "Workflow execution cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_workflow_templates():
    """Get available workflow templates."""
    try:
        templates = [
            {
                "id": "approval_workflow",
                "name": "Standard Approval",
                "description": "Standard approval workflow for requests",
                "category": "approval",
                "steps": [
                    {
                        "id": "send_approval_request",
                        "type": "send_notification",
                        "message": "Approval request sent",
                        "channel": "#approvals"
                    },
                    {
                        "id": "wait_for_approval",
                        "type": "wait_for_approval",
                        "approval_params": {
                            "request_type": "general",
                            "approval_channel": "#approvals"
                        }
                    },
                    {
                        "id": "send_result",
                        "type": "send_notification",
                        "message": "Approval decision received",
                        "channel": "#notifications"
                    }
                ]
            },
            {
                "id": "email_triage_workflow",
                "name": "Email Triage",
                "description": "Automated email processing and triage",
                "category": "communication",
                "steps": [
                    {
                        "id": "analyze_email",
                        "type": "ai_analysis",
                        "description": "Analyze email content with AI"
                    },
                    {
                        "id": "create_task_if_needed",
                        "type": "conditional_branch",
                        "condition": {
                            "type": "equals",
                            "left": {"type": "variable", "name": "requires_action"},
                            "right": True
                        },
                        "true_branch": [
                            {
                                "id": "create_task",
                                "type": "create_task",
                                "name": "Email Follow-up",
                                "project_id": "default"
                            }
                        ]
                    }
                ]
            },
            {
                "id": "task_creation_workflow",
                "name": "Task Creation",
                "description": "Automated task creation and assignment",
                "category": "project_management",
                "steps": [
                    {
                        "id": "create_task",
                        "type": "create_task",
                        "name": "New Task",
                        "project_id": "default"
                    },
                    {
                        "id": "notify_assignee",
                        "type": "send_notification",
                        "message": "New task assigned",
                        "user_id": "assignee"
                    }
                ]
            },
            {
                "id": "meeting_scheduling_workflow",
                "name": "Meeting Scheduling",
                "description": "Automated meeting scheduling and notifications",
                "category": "calendar",
                "steps": [
                    {
                        "id": "schedule_meeting",
                        "type": "calendar_schedule",
                        "title": "Meeting",
                        "attendees": "participants"
                    },
                    {
                        "id": "send_invitations",
                        "type": "send_notification",
                        "message": "Meeting invitation sent",
                        "channel": "#meetings"
                    }
                ]
            }
        ]
        
        return templates
        
    except Exception as e:
        logger.error(f"Error getting workflow templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/instantiate", response_model=WorkflowResponse)
async def instantiate_workflow_template(
    template_id: str,
    request: WorkflowCreateRequest,
    current_user: str = Depends(get_current_user),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Instantiate a workflow from a template."""
    try:
        # Get template
        templates = await get_workflow_templates()
        template = next((t for t in templates if t['id'] == template_id), None)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Create workflow from template
        workflow_id = await workflow_engine.create_workflow(
            name=request.name,
            description=request.description or template['description'],
            steps=template['steps'],
            triggers=request.triggers or ['manual'],
            is_active=request.is_active,
            metadata={
                'template_id': template_id,
                'category': template['category'],
                'created_from_template': True
            },
            created_by=current_user
        )
        
        # Get the created workflow
        workflow = workflow_engine.active_workflows.get(workflow_id)
        if not workflow:
            raise HTTPException(status_code=500, detail="Failed to retrieve created workflow")
        
        return WorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            steps=workflow.steps,
            triggers=workflow.triggers,
            is_active=workflow.is_active,
            metadata=workflow.metadata,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error instantiating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def workflow_health():
    """Health check endpoint for workflows."""
    return {
        "status": "healthy",
        "service": "workflow-engine",
        "active_workflows": 0,  # This would be dynamic
        "timestamp": datetime.now().isoformat()
    } 


async def route_slack_event(event: Dict[str, Any], team_id: str, db_session) -> None:
    """Route Slack events to appropriate workflows."""
    try:
        event_type = event.get("type")
        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        timestamp = event.get("ts")
        
        logger.info(f"Routing Slack event: {event_type} from user {user_id} in channel {channel_id}")
        
        # Create event log entry
        event_log = EventLog(
            platform="slack",
            event_type=event_type,
            user_id=user_id,
            channel_id=channel_id,
            content=text,
            timestamp=datetime.fromtimestamp(float(timestamp)) if timestamp else datetime.utcnow(),
            raw_data=event,
            processed=False
        )
        db_session.add(event_log)
        db_session.commit()
        
        # Route based on event type
        if event_type == "app_mention":
            await route_slack_mention(event, team_id, user_id, channel_id, text, db_session)
        elif event_type == "message":
            await route_slack_message(event, team_id, user_id, channel_id, text, db_session)
        elif event_type == "reaction_added":
            await route_slack_reaction(event, team_id, user_id, channel_id, db_session)
        else:
            logger.debug(f"Unhandled Slack event type: {event_type}")
            
        event_log.processed = True
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing Slack event: {e}", exc_info=True)


async def route_gmail_event(message: Dict[str, Any], user_id: str, db_session) -> None:
    """Route Gmail events to appropriate workflows."""
    try:
        message_id = message.get("id")
        thread_id = message.get("threadId")
        headers = message.get("payload", {}).get("headers", [])
        
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
        from_header = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
        to_header = next((h["value"] for h in headers if h["name"].lower() == "to"), "")
        
        logger.info(f"Routing Gmail event: message {message_id} from {from_header} to {to_header}")
        
        # Create event log entry
        event_log = EventLog(
            platform="gmail",
            event_type="email_received",
            user_id=user_id,
            content=subject,
            timestamp=datetime.utcnow(),
            raw_data=message,
            processed=False
        )
        db_session.add(event_log)
        db_session.commit()
        
        # Route based on email characteristics
        if is_urgent_email(subject, from_header):
            await route_urgent_email(message, user_id, db_session)
        elif is_meeting_email(subject):
            await route_meeting_email(message, user_id, db_session)
        elif is_task_email(subject):
            await route_task_email(message, user_id, db_session)
        else:
            await route_general_email(message, user_id, db_session)
            
        event_log.processed = True
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing Gmail event: {e}", exc_info=True)


async def route_asana_event(event: Dict[str, Any], webhook_id: str, db_session) -> None:
    """Route Asana events to appropriate workflows."""
    try:
        event_type = event.get("action")
        resource_type = event.get("resource", {}).get("resource_type")
        resource_id = event.get("resource", {}).get("gid")
        user_id = event.get("user", {}).get("gid")
        
        logger.info(f"Routing Asana event: {event_type} on {resource_type} {resource_id}")
        
        # Create event log entry
        event_log = EventLog(
            platform="asana",
            event_type=event_type,
            user_id=user_id,
            content=f"{event_type} on {resource_type}",
            timestamp=datetime.utcnow(),
            raw_data=event,
            processed=False
        )
        db_session.add(event_log)
        db_session.commit()
        
        # Route based on event type and resource
        if resource_type == "task":
            await route_task_event(event, resource_id, user_id, db_session)
        elif resource_type == "project":
            await route_project_event(event, resource_id, user_id, db_session)
        elif resource_type == "story":
            await route_story_event(event, resource_id, user_id, db_session)
        else:
            logger.debug(f"Unhandled Asana resource type: {resource_type}")
            
        event_log.processed = True
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing Asana event: {e}", exc_info=True)


async def route_slack_mention(
    event: Dict[str, Any], 
    team_id: str, 
    user_id: str, 
    channel_id: str, 
    text: str, 
    db_session
) -> None:
    """Route Slack app mentions to AI workflow."""
    try:
        # Extract the actual message content (remove bot mention)
        message_content = text.replace(f"<@{event.get('bot_id', '')}>", "").strip()
        
        if not message_content:
            logger.debug("Empty message content after removing bot mention")
            return
        
        logger.info(f"Processing Slack mention: {message_content}")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="slack_mention",
            trigger_user=user_id,
            trigger_channel=channel_id,
            trigger_content=message_content,
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Route to AI chain for processing
        ai_chain = get_ai_chain()
        response = await ai_chain.process_slack_message(
            message=message_content,
            user_id=user_id,
            channel_id=channel_id,
            team_id=team_id,
            workflow_id=workflow_exec.id
        )
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = response
        db_session.commit()
        
        logger.info(f"Completed Slack mention workflow {workflow_exec.id}")
        
    except Exception as e:
        logger.error(f"Error processing Slack mention: {e}", exc_info=True)


async def route_slack_message(
    event: Dict[str, Any], 
    team_id: str, 
    user_id: str, 
    channel_id: str, 
    text: str, 
    db_session
) -> None:
    """Route general Slack messages to appropriate workflows."""
    try:
        # Check if message contains keywords that need attention
        if contains_urgent_keywords(text):
            await route_urgent_slack_message(event, team_id, user_id, channel_id, text, db_session)
        elif contains_meeting_keywords(text):
            await route_meeting_slack_message(event, team_id, user_id, channel_id, text, db_session)
        elif contains_task_keywords(text):
            await route_task_slack_message(event, team_id, user_id, channel_id, text, db_session)
        else:
            logger.debug(f"General Slack message, no specific routing needed")
            
    except Exception as e:
        logger.error(f"Error routing Slack message: {e}", exc_info=True)


async def route_slack_reaction(
    event: Dict[str, Any], 
    team_id: str, 
    user_id: str, 
    channel_id: str, 
    db_session
) -> None:
    """Route Slack reactions to appropriate workflows."""
    try:
        reaction = event.get("reaction")
        item_type = event.get("item", {}).get("type")
        item_ts = event.get("item", {}).get("ts")
        
        logger.info(f"Processing Slack reaction: {reaction} on {item_type}")
        
        # Route based on reaction type
        if reaction in ["white_check_mark", "heavy_check_mark"]:
            await route_approval_reaction(event, team_id, user_id, channel_id, db_session)
        elif reaction in ["x", "negative_squared_cross_mark"]:
            await route_rejection_reaction(event, team_id, user_id, channel_id, db_session)
        elif reaction in ["eyes", "bulb"]:
            await route_attention_reaction(event, team_id, user_id, channel_id, db_session)
            
    except Exception as e:
        logger.error(f"Error routing Slack reaction: {e}", exc_info=True)


async def route_urgent_email(message: Dict[str, Any], user_id: str, db_session) -> None:
    """Route urgent emails to immediate attention workflow."""
    try:
        logger.info(f"Routing urgent email for immediate attention")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="urgent_email",
            trigger_user=user_id,
            trigger_content="Urgent email received",
            status="started",
            started_at=datetime.utcnow(),
            priority="high"
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # TODO: Implement urgent email workflow
        # This could include:
        # - Immediate notifications
        # - Task creation
        # - Escalation procedures
        
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing urgent email: {e}", exc_info=True)


async def route_meeting_email(message: Dict[str, Any], user_id: str, db_session) -> None:
    """Route meeting-related emails to meeting workflow."""
    try:
        logger.info(f"Routing meeting email")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="meeting_email",
            trigger_user=user_id,
            trigger_content="Meeting email received",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # TODO: Implement meeting email workflow
        # This could include:
        # - Calendar integration
        # - Meeting scheduling
        # - Follow-up reminders
        
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing meeting email: {e}", exc_info=True)


async def route_task_email(message: Dict[str, Any], user_id: str, db_session) -> None:
    """Route task-related emails to task workflow."""
    try:
        logger.info(f"Routing task email")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="task_email",
            trigger_user=user_id,
            trigger_content="Task email received",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # TODO: Implement task email workflow
        # This could include:
        # - Task creation in Asana
        # - Priority assignment
        # - Deadline setting
        
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing task email: {e}", exc_info=True)


async def route_general_email(message: Dict[str, Any], user_id: str, db_session) -> None:
    """Route general emails to standard processing workflow."""
    try:
        logger.info(f"Routing general email")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="general_email",
            trigger_user=user_id,
            trigger_content="General email received",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # TODO: Implement general email workflow
        # This could include:
        # - Content analysis
        # - Categorization
        # - Archive or follow-up decisions
        
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error routing general email: {e}", exc_info=True)


async def route_task_event(event: Dict[str, Any], task_id: str, user_id: str, db_session) -> None:
    """Route Asana task events to appropriate workflows."""
    try:
        event_type = event.get("action")
        
        if event_type == "created":
            await route_task_created(event, task_id, user_id, db_session)
        elif event_type == "changed":
            await route_task_changed(event, task_id, user_id, db_session)
        elif event_type == "completed":
            await route_task_completed(event, task_id, user_id, db_session)
        elif event_type == "assigned":
            await route_task_assigned(event, task_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error routing task event: {e}", exc_info=True)


async def route_project_event(event: Dict[str, Any], project_id: str, user_id: str, db_session) -> None:
    """Route Asana project events to appropriate workflows."""
    try:
        event_type = event.get("action")
        
        if event_type == "created":
            await route_project_created(event, project_id, user_id, db_session)
        elif event_type == "changed":
            await route_project_changed(event, project_id, user_id, db_session)
        elif event_type == "archived":
            await route_project_archived(event, project_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error routing project event: {e}", exc_info=True)


async def route_story_event(event: Dict[str, Any], story_id: str, user_id: str, db_session) -> None:
    """Route Asana story events to appropriate workflows."""
    try:
        event_type = event.get("action")
        story_type = event.get("resource_subtype")
        
        if story_type == "comment_added":
            await route_comment_added(event, story_id, user_id, db_session)
        elif story_type == "status_changed":
            await route_status_changed(event, story_id, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error routing story event: {e}", exc_info=True)


# Helper functions for routing decisions
def is_urgent_email(subject: str, from_header: str) -> bool:
    """Check if an email is urgent based on subject and sender."""
    urgent_keywords = ["urgent", "asap", "emergency", "critical", "immediate"]
    urgent_senders = ["ceo", "cto", "manager", "boss"]
    
    subject_lower = subject.lower()
    from_lower = from_header.lower()
    
    return any(keyword in subject_lower for keyword in urgent_keywords) or \
           any(sender in from_lower for sender in urgent_senders)


def is_meeting_email(subject: str) -> bool:
    """Check if an email is meeting-related."""
    meeting_keywords = ["meeting", "call", "conference", "sync", "standup", "review"]
    subject_lower = subject.lower()
    
    return any(keyword in subject_lower for keyword in meeting_keywords)


def is_task_email(subject: str) -> bool:
    """Check if an email is task-related."""
    task_keywords = ["task", "todo", "action item", "follow up", "deadline", "due"]
    subject_lower = subject.lower()
    
    return any(keyword in subject_lower for keyword in task_keywords)


def contains_urgent_keywords(text: str) -> bool:
    """Check if Slack message contains urgent keywords."""
    urgent_keywords = ["urgent", "asap", "help", "blocked", "issue", "problem"]
    text_lower = text.lower()
    
    return any(keyword in text_lower for keyword in urgent_keywords)


def contains_meeting_keywords(text: str) -> bool:
    """Check if Slack message contains meeting keywords."""
    meeting_keywords = ["meeting", "call", "sync", "standup", "review"]
    text_lower = text.lower()
    
    return any(keyword in text_lower for keyword in meeting_keywords)


def contains_task_keywords(text: str) -> bool:
    """Check if Slack message contains task keywords."""
    task_keywords = ["task", "todo", "action", "follow up", "deadline"]
    text_lower = text.lower()
    
    return any(keyword in text_lower for keyword in task_keywords)


# Placeholder functions for specific workflow routing
async def route_urgent_slack_message(event, team_id, user_id, channel_id, text, db_session):
    """Route urgent Slack messages."""
    logger.info(f"Routing urgent Slack message: {text}")
    # TODO: Implement urgent message workflow


async def route_meeting_slack_message(event, team_id, user_id, channel_id, text, db_session):
    """Route meeting-related Slack messages."""
    logger.info(f"Routing meeting Slack message: {text}")
    # TODO: Implement meeting message workflow


async def route_task_slack_message(event, team_id, user_id, channel_id, text, db_session):
    """Route task-related Slack messages."""
    logger.info(f"Routing task Slack message: {text}")
    # TODO: Implement task message workflow


async def route_approval_reaction(event, team_id, user_id, channel_id, db_session):
    """Route approval reactions."""
    logger.info(f"Routing approval reaction")
    # TODO: Implement approval workflow


async def route_rejection_reaction(event, team_id, user_id, channel_id, db_session):
    """Route rejection reactions."""
    logger.info(f"Routing rejection reaction")
    # TODO: Implement rejection workflow


async def route_attention_reaction(event, team_id, user_id, channel_id, db_session):
    """Route attention reactions."""
    logger.info(f"Routing attention reaction")
    # TODO: Implement attention workflow


async def route_task_created(event, task_id, user_id, db_session):
    """Route task creation events."""
    logger.info(f"Routing task creation: {task_id}")
    # TODO: Implement task creation workflow


async def route_task_changed(event, task_id, user_id, db_session):
    """Route task change events."""
    logger.info(f"Routing task change: {task_id}")
    # TODO: Implement task change workflow


async def route_task_completed(event, task_id, user_id, db_session):
    """Route task completion events."""
    logger.info(f"Routing task completion: {task_id}")
    # TODO: Implement task completion workflow


async def route_task_assigned(event, task_id, user_id, db_session):
    """Route task assignment events."""
    logger.info(f"Routing task assignment: {task_id}")
    # TODO: Implement task assignment workflow


async def route_project_created(event, project_id, user_id, db_session):
    """Route project creation events."""
    logger.info(f"Routing project creation: {project_id}")
    # TODO: Implement project creation workflow


async def route_project_changed(event, project_id, user_id, db_session):
    """Route project change events."""
    logger.info(f"Routing project change: {project_id}")
    # TODO: Implement project change workflow


async def route_project_archived(event, project_id, user_id, db_session):
    """Route project archival events."""
    logger.info(f"Routing project archival: {project_id}")
    # TODO: Implement project archival workflow


async def route_comment_added(event, story_id, user_id, db_session):
    """Route comment addition events."""
    logger.info(f"Routing comment addition: {story_id}")
    # TODO: Implement comment workflow


async def route_status_changed(event, story_id, user_id, db_session):
    """Route status change events."""
    logger.info(f"Routing status change: {story_id}")
    # TODO: Implement status change workflow 