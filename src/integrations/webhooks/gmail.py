"""Gmail webhook handler for Reflex Executive Assistant."""

import logging
import base64
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse

from ...config import get_settings
from ...storage.models import GmailEvent, Email, User
from ...storage.db import get_db_session
from ...workflows.router import route_gmail_event
from ...integrations.gmail_client import get_gmail_client
from ...auth.dependencies import verify_gmail_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/notifications")
async def handle_gmail_notifications(
    request: Request,
    db_session = Depends(get_db_session),
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_channel_expiration: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_uri: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None)
):
    """Handle Gmail push notifications."""
    try:
        # Verify Gmail webhook
        await verify_gmail_webhook(request)
        
        # Extract webhook metadata
        webhook_data = {
            "channel_id": x_goog_channel_id,
            "channel_token": x_goog_channel_token,
            "channel_expiration": x_goog_channel_expiration,
            "resource_id": x_goog_resource_id,
            "resource_uri": x_goog_resource_uri,
            "resource_state": x_goog_resource_state
        }
        
        logger.info(f"Received Gmail notification: {webhook_data}")
        
        # Parse the notification payload
        payload = await request.json()
        
        # Store webhook event in database
        gmail_event = GmailEvent(
            channel_id=x_goog_channel_id,
            resource_id=x_goog_resource_id,
            resource_uri=x_goog_resource_uri,
            resource_state=x_goog_resource_state,
            webhook_data=webhook_data,
            notification_payload=payload,
            processed=False
        )
        db_session.add(gmail_event)
        db_session.commit()
        
        # Process the notification based on resource state
        if x_goog_resource_state == "sync":
            await process_gmail_sync(x_goog_resource_uri, db_session)
        elif x_goog_resource_state == "exists":
            await process_gmail_exists(x_goog_resource_uri, db_session)
        elif x_goog_resource_state == "not_exists":
            await process_gmail_not_exists(x_goog_resource_uri, db_session)
        
        gmail_event.processed = True
        db_session.commit()
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Gmail notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/watch")
async def setup_gmail_watch(
    request: Request,
    db_session = Depends(get_db_session)
):
    """Set up Gmail push notifications for a user."""
    try:
        # Verify Gmail webhook
        await verify_gmail_webhook(request)
        
        # Parse the watch request
        payload = await request.json()
        user_id = payload.get("user_id")
        topic_name = payload.get("topic_name")
        
        if not user_id or not topic_name:
            raise HTTPException(status_code=400, detail="Missing user_id or topic_name")
        
        # Set up Gmail watch for the user
        gmail_client = get_gmail_client()
        watch_response = await gmail_client.setup_watch(
            user_id=user_id,
            topic_name=topic_name
        )
        
        # Store watch configuration
        # TODO: Implement watch storage in database
        
        logger.info(f"Set up Gmail watch for user {user_id}")
        
        return {
            "status": "ok",
            "watch_response": watch_response
        }
        
    except Exception as e:
        logger.error(f"Error setting up Gmail watch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stop")
async def stop_gmail_watch(
    request: Request,
    db_session = Depends(get_db_session)
):
    """Stop Gmail push notifications for a user."""
    try:
        # Verify Gmail webhook
        await verify_gmail_webhook(request)
        
        # Parse the stop request
        payload = await request.json()
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user_id")
        
        # Stop Gmail watch for the user
        gmail_client = get_gmail_client()
        await gmail_client.stop_watch(user_id=user_id)
        
        # Remove watch configuration
        # TODO: Implement watch removal from database
        
        logger.info(f"Stopped Gmail watch for user {user_id}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error stopping Gmail watch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_gmail_sync(resource_uri: str, db_session) -> None:
    """Process Gmail sync notification."""
    try:
        logger.info(f"Processing Gmail sync for resource: {resource_uri}")
        
        # Extract user ID from resource URI
        # Format: https://gmail.googleapis.com/gmail/v1/users/{user_id}/messages
        user_id = resource_uri.split("/users/")[1].split("/")[0]
        
        # Get recent messages for the user
        gmail_client = get_gmail_client()
        messages = await gmail_client.get_recent_messages(user_id, max_results=10)
        
        for message in messages:
            await process_gmail_message(message, user_id, db_session)
            
    except Exception as e:
        logger.error(f"Error processing Gmail sync: {e}", exc_info=True)


async def process_gmail_exists(resource_uri: str, db_session) -> None:
    """Process Gmail exists notification."""
    try:
        logger.info(f"Processing Gmail exists for resource: {resource_uri}")
        
        # Extract message ID from resource URI
        # Format: https://gmail.googleapis.com/gmail/v1/users/{user_id}/messages/{message_id}
        parts = resource_uri.split("/messages/")
        if len(parts) == 2:
            user_id = parts[0].split("/users/")[1]
            message_id = parts[1]
            
            # Get the specific message
            gmail_client = get_gmail_client()
            message = await gmail_client.get_message(user_id, message_id)
            
            if message:
                await process_gmail_message(message, user_id, db_session)
                
    except Exception as e:
        logger.error(f"Error processing Gmail exists: {e}", exc_info=True)


async def process_gmail_not_exists(resource_uri: str, db_session) -> None:
    """Process Gmail not exists notification."""
    try:
        logger.info(f"Processing Gmail not exists for resource: {resource_uri}")
        
        # This typically means a message was deleted
        # Extract message ID and mark as deleted in database
        parts = resource_uri.split("/messages/")
        if len(parts) == 2:
            user_id = parts[0].split("/users/")[1]
            message_id = parts[1]
            
            # Mark message as deleted in database
            # TODO: Implement message deletion tracking
            
            logger.info(f"Message {message_id} for user {user_id} was deleted")
            
    except Exception as e:
        logger.error(f"Error processing Gmail not exists: {e}", exc_info=True)


async def process_gmail_message(message: Dict[str, Any], user_id: str, db_session) -> None:
    """Process a Gmail message."""
    try:
        message_id = message.get("id")
        thread_id = message.get("threadId")
        
        # Check if message already exists in database
        existing_email = db_session.query(Email).filter(
            Email.gmail_message_id == message_id
        ).first()
        
        if existing_email:
            logger.debug(f"Message {message_id} already processed")
            return
        
        # Extract message details
        headers = message.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
        from_header = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
        to_header = next((h["value"] for h in headers if h["name"].lower() == "to"), "")
        date_header = next((h["value"] for h in headers if h["name"].lower() == "date"), "")
        
        # Parse sender and recipient
        sender = parse_email_address(from_header)
        recipients = parse_email_addresses(to_header)
        
        # Store email in database
        email = Email(
            gmail_message_id=message_id,
            gmail_thread_id=thread_id,
            user_id=user_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            received_date=date_header,
            message_data=message,
            processed=False
        )
        db_session.add(email)
        db_session.commit()
        
        # Route to appropriate workflow
        await route_gmail_event(message, user_id, db_session)
        
        email.processed = True
        db_session.commit()
        
        logger.info(f"Processed Gmail message {message_id}: {subject}")
        
    except Exception as e:
        logger.error(f"Error processing Gmail message: {e}", exc_info=True)


def parse_email_address(email_string: str) -> str:
    """Parse email address from email string."""
    if not email_string:
        return ""
    
    # Handle formats like "John Doe <john@example.com>" or "john@example.com"
    if "<" in email_string and ">" in email_string:
        start = email_string.find("<") + 1
        end = email_string.find(">")
        return email_string[start:end].strip()
    
    return email_string.strip()


def parse_email_addresses(email_string: str) -> list:
    """Parse multiple email addresses from email string."""
    if not email_string:
        return []
    
    # Split by comma and parse each address
    addresses = [addr.strip() for addr in email_string.split(",")]
    return [parse_email_address(addr) for addr in addresses if addr]


@router.get("/health")
async def gmail_webhook_health():
    """Health check endpoint for Gmail webhooks."""
    return {"status": "healthy", "service": "gmail-webhooks"} 