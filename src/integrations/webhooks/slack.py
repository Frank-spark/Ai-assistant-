"""Slack webhook handler for Reflex Executive Assistant."""

import logging
import hmac
import hashlib
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse

from ...config import get_settings
from ...storage.models import SlackEvent, User
from ...storage.db import get_db_session
from ...workflows.router import route_slack_event
from ...auth.dependencies import verify_slack_signature

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/events")
async def handle_slack_events(
    request: Request,
    db_session = Depends(get_db_session)
):
    """Handle Slack Events API webhook events."""
    try:
        # Verify Slack signature
        await verify_slack_signature(request)
        
        # Parse the event payload
        payload = await request.json()
        logger.info(f"Received Slack event: {payload.get('type', 'unknown')}")
        
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}
        
        # Extract event data
        event = payload.get("event", {})
        event_type = event.get("type")
        team_id = payload.get("team_id")
        
        # Store event in database
        slack_event = SlackEvent(
            team_id=team_id,
            event_type=event_type,
            event_data=event,
            raw_payload=payload,
            processed=False
        )
        db_session.add(slack_event)
        db_session.commit()
        
        # Route event to appropriate workflow
        if event_type in ["app_mention", "message", "reaction_added"]:
            await route_slack_event(event, team_id, db_session)
            slack_event.processed = True
            db_session.commit()
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/interactive")
async def handle_slack_interactive(
    request: Request,
    db_session = Depends(get_db_session)
):
    """Handle Slack interactive components (buttons, menus, etc.)."""
    try:
        # Verify Slack signature
        await verify_slack_signature(request)
        
        # Parse form data
        form_data = await request.form()
        payload = form_data.get("payload")
        
        if not payload:
            raise HTTPException(status_code=400, detail="Missing payload")
        
        import json
        payload_data = json.loads(payload)
        
        # Handle different interactive component types
        component_type = payload_data.get("type")
        
        if component_type == "block_actions":
            # Handle button clicks, menu selections
            await handle_block_actions(payload_data, db_session)
        elif component_type == "view_submission":
            # Handle modal submissions
            await handle_view_submission(payload_data, db_session)
        elif component_type == "shortcut":
            # Handle global shortcuts
            await handle_shortcut(payload_data, db_session)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Slack interactive: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_block_actions(payload: Dict[str, Any], db_session) -> None:
    """Handle Slack block actions (buttons, menus, etc.)."""
    actions = payload.get("actions", [])
    user_id = payload.get("user", {}).get("id")
    channel_id = payload.get("channel", {}).get("id")
    
    for action in actions:
        action_id = action.get("action_id")
        action_value = action.get("value")
        
        logger.info(f"Processing Slack action: {action_id} = {action_value}")
        
        # Route to appropriate handler based on action_id
        if action_id.startswith("approve_"):
            await handle_approval_action(action_id, action_value, user_id, channel_id, db_session)
        elif action_id.startswith("reject_"):
            await handle_rejection_action(action_id, action_value, user_id, channel_id, db_session)
        elif action_id.startswith("create_task_"):
            await handle_create_task_action(action_id, action_value, user_id, channel_id, db_session)


async def handle_view_submission(payload: Dict[str, Any], db_session) -> None:
    """Handle Slack modal submissions."""
    view = payload.get("view", {})
    callback_id = view.get("callback_id")
    user_id = payload.get("user", {}).get("id")
    
    logger.info(f"Processing Slack modal submission: {callback_id}")
    
    # Extract form values
    state = view.get("state", {}).get("values", {})
    
    # Route to appropriate handler based on callback_id
    if callback_id == "create_task_modal":
        await handle_create_task_modal(state, user_id, db_session)
    elif callback_id == "schedule_meeting_modal":
        await handle_schedule_meeting_modal(state, user_id, db_session)


async def handle_shortcut(payload: Dict[str, Any], db_session) -> None:
    """Handle Slack global shortcuts."""
    callback_id = payload.get("callback_id")
    user_id = payload.get("user", {}).get("id")
    
    logger.info(f"Processing Slack shortcut: {callback_id}")
    
    # Route to appropriate handler based on callback_id
    if callback_id == "create_quick_task":
        await handle_quick_task_shortcut(user_id, db_session)
    elif callback_id == "schedule_meeting":
        await handle_schedule_meeting_shortcut(user_id, db_session)


async def handle_approval_action(
    action_id: str, 
    action_value: str, 
    user_id: str, 
    channel_id: str, 
    db_session
) -> None:
    """Handle approval actions from Slack interactive components."""
    # Extract the item being approved from action_id
    # Format: approve_{item_type}_{item_id}
    parts = action_id.split("_")
    if len(parts) >= 3:
        item_type = parts[1]
        item_id = parts[2]
        
        logger.info(f"User {user_id} approved {item_type} {item_id}")
        
        # TODO: Implement approval logic
        # This would typically update the approval status in the database
        # and trigger the approved action (send email, create task, etc.)
        
        # Send confirmation to the channel
        # await send_slack_message(channel_id, f"✅ Approved by <@{user_id}>")


async def handle_rejection_action(
    action_id: str, 
    action_value: str, 
    user_id: str, 
    channel_id: str, 
    db_session
) -> None:
    """Handle rejection actions from Slack interactive components."""
    parts = action_id.split("_")
    if len(parts) >= 3:
        item_type = parts[1]
        item_id = parts[2]
        
        logger.info(f"User {user_id} rejected {item_type} {item_id}")
        
        # TODO: Implement rejection logic
        # This would typically update the approval status and notify relevant parties
        
        # Send confirmation to the channel
        # await send_slack_message(channel_id, f"❌ Rejected by <@{user_id}>")


async def handle_create_task_action(
    action_id: str, 
    action_value: str, 
    user_id: str, 
    channel_id: str, 
    db_session
) -> None:
    """Handle create task actions from Slack interactive components."""
    logger.info(f"User {user_id} requested task creation via {action_id}")
    
    # TODO: Implement task creation logic
    # This would typically open a modal for task details or create a task directly


async def handle_create_task_modal(state: Dict[str, Any], user_id: str, db_session) -> None:
    """Handle task creation modal submission."""
    logger.info(f"Processing task creation modal from user {user_id}")
    
    # TODO: Extract form values and create task
    # This would typically create an Asana task and notify relevant parties


async def handle_schedule_meeting_modal(state: Dict[str, Any], user_id: str, db_session) -> None:
    """Handle meeting scheduling modal submission."""
    logger.info(f"Processing meeting scheduling modal from user {user_id}")
    
    # TODO: Extract form values and schedule meeting
    # This would typically create a calendar event and send invites


async def handle_quick_task_shortcut(user_id: str, db_session) -> None:
    """Handle quick task creation shortcut."""
    logger.info(f"Processing quick task shortcut from user {user_id}")
    
    # TODO: Implement quick task creation
    # This would typically open a simple modal or create a task with defaults


async def handle_schedule_meeting_shortcut(user_id: str, db_session) -> None:
    """Handle meeting scheduling shortcut."""
    logger.info(f"Processing meeting scheduling shortcut from user {user_id}")
    
    # TODO: Implement meeting scheduling
    # This would typically open a modal for meeting details 