"""Slack background tasks for Reflex Executive Assistant."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import current_task

from ..config import get_settings
from ..integrations.slack_client import get_slack_client
from ..storage.db import get_db_session
from ..storage.models import SlackMessage, SlackChannel, SlackUser, WorkflowExecution
from ..ai.chain import get_ai_chain
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.jobs.tasks.slack_tasks.sync_slack")
def sync_slack(self) -> Dict[str, Any]:
    """Sync Slack messages and update channel/user information."""
    try:
        logger.info("Starting Slack synchronization")
        current_task.update_state(state="PROGRESS", meta={"status": "syncing"})
        
        slack_client = get_slack_client()
        db_session = get_db_session()
        
        # Sync channels
        channels = slack_client.get_channels()
        channel_count = 0
        for channel_data in channels:
            try:
                channel = _sync_channel(channel_data, db_session)
                if channel:
                    channel_count += 1
            except Exception as e:
                logger.error(f"Error syncing channel {channel_data.get('id')}: {e}")
                continue
        
        # Sync users
        users = slack_client.get_users()
        user_count = 0
        for user_data in users:
            try:
                user = _sync_user(user_data, db_session)
                if user:
                    user_count += 1
            except Exception as e:
                logger.error(f"Error syncing user {user_data.get('id')}: {e}")
                continue
        
        # Sync recent messages from active channels
        message_count = 0
        active_channels = db_session.query(SlackChannel).filter(
            SlackChannel.is_archived == False
        ).all()
        
        for channel in active_channels:
            try:
                messages = slack_client.get_channel_messages(channel.slack_id, limit=50)
                for message_data in messages:
                    if _should_process_message(message_data):
                        message = _sync_message(message_data, channel.slack_id, db_session)
                        if message:
                            message_count += 1
                            
                            # Process with AI if it's a mention or important message
                            if _is_important_message(message_data):
                                _process_message_ai(message, message_data)
            except Exception as e:
                logger.error(f"Error syncing messages for channel {channel.slack_id}: {e}")
                continue
        
        db_session.close()
        
        result = {
            "status": "completed",
            "channels_synced": channel_count,
            "users_synced": user_count,
            "messages_synced": message_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Slack sync completed: {channel_count} channels, {user_count} users, {message_count} messages")
        return result
        
    except Exception as e:
        logger.error(f"Slack sync failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.slack_tasks.process_message")
def process_message(self, message_id: str, user_id: str, channel_id: str) -> Dict[str, Any]:
    """Process a specific Slack message with AI."""
    try:
        logger.info(f"Processing Slack message {message_id} from user {user_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "processing"})
        
        db_session = get_db_session()
        
        # Get message
        message = db_session.query(SlackMessage).filter(SlackMessage.id == message_id).first()
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="slack_message",
            trigger_user=user_id,
            trigger_channel=channel_id,
            trigger_content=message.text,
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Process with AI
        ai_chain = get_ai_chain()
        result = ai_chain.process_slack_message(
            message=message.text,
            user_id=user_id,
            channel_id=channel_id,
            team_id=message.team_id,
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
            "message_id": message_id,
            "workflow_id": workflow_exec.id,
            "ai_result": result
        }
        
    except Exception as e:
        logger.error(f"Slack message processing failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.slack_tasks.send_message")
def send_message(self, channel: str, message: str, user_id: str) -> Dict[str, Any]:
    """Send a Slack message in the background."""
    try:
        logger.info(f"Sending Slack message to channel {channel}")
        current_task.update_state(state="PROGRESS", meta={"status": "sending"})
        
        slack_client = get_slack_client()
        
        # Send message
        result = slack_client.send_message(channel, message)
        
        # Store in database
        db_session = get_db_session()
        
        slack_message = SlackMessage(
            slack_id=result.get("ts") if result else None,
            text=message,
            user_id=user_id,
            channel_id=channel,
            team_id=result.get("team") if result else None,
            message_type="outbound",
            timestamp=datetime.utcnow(),
            metadata=result or {}
        )
        db_session.add(slack_message)
        db_session.commit()
        db_session.close()
        
        return {
            "status": "sent",
            "message_id": slack_message.id,
            "slack_ts": result.get("ts") if result else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Slack message sending failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.slack_tasks.monitor_channels")
def monitor_channels(self) -> Dict[str, Any]:
    """Monitor Slack channels for activity and important messages."""
    try:
        logger.info("Starting channel monitoring")
        current_task.update_state(state="PROGRESS", meta={"status": "monitoring"})
        
        slack_client = get_slack_client()
        db_session = get_db_session()
        
        # Get active channels
        active_channels = db_session.query(SlackChannel).filter(
            SlackChannel.is_archived == False,
            SlackChannel.is_private == False
        ).all()
        
        monitored_count = 0
        important_messages = 0
        
        for channel in active_channels:
            try:
                # Get recent messages
                messages = slack_client.get_channel_messages(channel.slack_id, limit=20)
                
                for message_data in messages:
                    if _is_important_message(message_data):
                        important_messages += 1
                        
                        # Check if message already processed
                        existing = db_session.query(SlackMessage).filter(
                            SlackMessage.slack_id == message_data.get("ts"),
                            SlackMessage.channel_id == channel.slack_id
                        ).first()
                        
                        if not existing:
                            # Process new important message
                            message = _sync_message(message_data, channel.slack_id, db_session)
                            if message:
                                _process_message_ai(message, message_data)
                
                monitored_count += 1
                
            except Exception as e:
                logger.error(f"Error monitoring channel {channel.slack_id}: {e}")
                continue
        
        db_session.close()
        
        return {
            "status": "completed",
            "channels_monitored": monitored_count,
            "important_messages_found": important_messages,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Channel monitoring failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.slack_tasks.update_user_status")
def update_user_status(self) -> Dict[str, Any]:
    """Update Slack user status and presence information."""
    try:
        logger.info("Updating user status information")
        current_task.update_state(state="PROGRESS", meta={"status": "updating"})
        
        slack_client = get_slack_client()
        db_session = get_db_session()
        
        # Get all users
        users = db_session.query(SlackUser).all()
        updated_count = 0
        
        for user in users:
            try:
                # Get current user info from Slack
                user_info = slack_client.get_user_info(user.slack_id)
                
                if user_info:
                    # Update user status
                    user.status = user_info.get("profile", {}).get("status_text", "")
                    user.status_emoji = user_info.get("profile", {}).get("status_emoji", "")
                    user.is_online = user_info.get("presence") == "active"
                    user.updated_at = datetime.utcnow()
                    
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Error updating user {user.slack_id}: {e}")
                continue
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "users_updated": updated_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"User status update failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.slack_tasks.cleanup_old_messages")
def cleanup_old_messages(self, days_old: int = 90) -> Dict[str, Any]:
    """Clean up old Slack messages from the database."""
    try:
        logger.info(f"Cleaning up Slack messages older than {days_old} days")
        current_task.update_state(state="PROGRESS", meta={"status": "cleaning"})
        
        db_session = get_db_session()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count messages to be deleted
        old_messages_count = db_session.query(SlackMessage).filter(
            SlackMessage.timestamp < cutoff_date
        ).count()
        
        # Delete old messages
        deleted_count = db_session.query(SlackMessage).filter(
            SlackMessage.timestamp < cutoff_date
        ).delete()
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "old_messages_count": old_messages_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Slack message cleanup failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


# Helper functions
def _sync_channel(channel_data: Dict[str, Any], db_session) -> Optional[SlackChannel]:
    """Sync a Slack channel to the database."""
    try:
        # Check if channel exists
        existing = db_session.query(SlackChannel).filter(
            SlackChannel.slack_id == channel_data.get("id")
        ).first()
        
        if existing:
            # Update existing channel
            existing.name = channel_data.get("name", existing.name)
            existing.purpose = channel_data.get("purpose", {}).get("value", existing.purpose)
            existing.topic = channel_data.get("topic", {}).get("value", existing.topic)
            existing.member_count = channel_data.get("num_members", existing.member_count)
            existing.is_archived = channel_data.get("is_archived", existing.is_archived)
            existing.is_private = channel_data.get("is_private", existing.is_private)
            existing.updated_at = datetime.utcnow()
            existing.metadata = channel_data
            
            return existing
        else:
            # Create new channel
            channel = SlackChannel(
                slack_id=channel_data.get("id"),
                name=channel_data.get("name", "unknown"),
                purpose=channel_data.get("purpose", {}).get("value", ""),
                topic=channel_data.get("topic", {}).get("value", ""),
                member_count=channel_data.get("num_members", 0),
                is_archived=channel_data.get("is_archived", False),
                is_private=channel_data.get("is_private", False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=channel_data
            )
            
            db_session.add(channel)
            db_session.commit()
            return channel
            
    except Exception as e:
        logger.error(f"Error syncing channel: {e}")
        db_session.rollback()
        return None


def _sync_user(user_data: Dict[str, Any], db_session) -> Optional[SlackUser]:
    """Sync a Slack user to the database."""
    try:
        # Check if user exists
        existing = db_session.query(SlackUser).filter(
            SlackUser.slack_id == user_data.get("id")
        ).first()
        
        if existing:
            # Update existing user
            existing.name = user_data.get("name", existing.name)
            existing.real_name = user_data.get("real_name", existing.real_name)
            existing.display_name = user_data.get("profile", {}).get("display_name", existing.display_name)
            existing.title = user_data.get("profile", {}).get("title", existing.title)
            existing.email = user_data.get("profile", {}).get("email", existing.email)
            existing.is_bot = user_data.get("is_bot", existing.is_bot)
            existing.is_admin = user_data.get("is_admin", existing.is_admin)
            existing.updated_at = datetime.utcnow()
            existing.metadata = user_data
            
            return existing
        else:
            # Create new user
            user = SlackUser(
                slack_id=user_data.get("id"),
                name=user_data.get("name", "unknown"),
                real_name=user_data.get("real_name", ""),
                display_name=user_data.get("profile", {}).get("display_name", ""),
                title=user_data.get("profile", {}).get("title", ""),
                email=user_data.get("profile", {}).get("email", ""),
                is_bot=user_data.get("is_bot", False),
                is_admin=user_data.get("is_admin", False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=user_data
            )
            
            db_session.add(user)
            db_session.commit()
            return user
            
    except Exception as e:
        logger.error(f"Error syncing user: {e}")
        db_session.rollback()
        return None


def _sync_message(message_data: Dict[str, Any], channel_id: str, db_session) -> Optional[SlackMessage]:
    """Sync a Slack message to the database."""
    try:
        # Check if message exists
        existing = db_session.query(SlackMessage).filter(
            SlackMessage.slack_id == message_data.get("ts"),
            SlackMessage.channel_id == channel_id
        ).first()
        
        if existing:
            return existing
        
        # Create new message
        message = SlackMessage(
            slack_id=message_data.get("ts"),
            text=message_data.get("text", ""),
            user_id=message_data.get("user", "unknown"),
            channel_id=channel_id,
            team_id=message_data.get("team", ""),
            message_type="inbound",
            timestamp=datetime.fromtimestamp(float(message_data.get("ts", 0))),
            thread_ts=message_data.get("thread_ts"),
            parent_user_id=message_data.get("parent_user_id"),
            metadata=message_data
        )
        
        db_session.add(message)
        db_session.commit()
        return message
        
    except Exception as e:
        logger.error(f"Error syncing message: {e}")
        db_session.rollback()
        return None


def _should_process_message(message_data: Dict[str, Any]) -> bool:
    """Determine if a message should be processed."""
    # Skip bot messages
    if message_data.get("bot_id"):
        return False
    
    # Skip messages with minimal content
    text = message_data.get("text", "")
    if len(text.strip()) < 10:
        return False
    
    # Skip system messages
    if message_data.get("subtype") in ["bot_message", "system_message", "channel_join", "channel_leave"]:
        return False
    
    return True


def _is_important_message(message_data: Dict[str, Any]) -> bool:
    """Determine if a message is important and should be processed with AI."""
    text = message_data.get("text", "").lower()
    
    # Check for mentions
    if "<@" in text:
        return True
    
    # Check for important keywords
    important_keywords = [
        "urgent", "important", "help", "question", "issue", "problem",
        "deadline", "meeting", "call", "review", "approval", "decision"
    ]
    
    if any(keyword in text for keyword in important_keywords):
        return True
    
    # Check for questions
    if "?" in text:
        return True
    
    return False


def _process_message_ai(message: SlackMessage, message_data: Dict[str, Any]) -> None:
    """Process message with AI for analysis."""
    try:
        # Queue AI processing task
        process_message.delay(
            message_id=str(message.id),
            user_id=message.user_id,
            channel_id=message.channel_id
        )
        
    except Exception as e:
        logger.error(f"Error queuing message AI processing: {e}") 