"""Email background tasks for Reflex Executive Assistant."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import current_task

from ..config import get_settings
from ..integrations.gmail_client import get_gmail_client
from ..storage.db import get_db_session
from ..storage.models import Email, EmailAttachment, WorkflowExecution
from ..ai.chain import get_ai_chain
from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="src.jobs.tasks.email_tasks.sync_email")
def sync_email(self) -> Dict[str, Any]:
    """Sync emails from Gmail and process them."""
    try:
        logger.info("Starting email synchronization")
        current_task.update_state(state="PROGRESS", meta={"status": "syncing"})
        
        gmail_client = get_gmail_client()
        db_session = get_db_session()
        
        # Get recent emails
        emails = gmail_client.get_recent_emails(max_results=50)
        
        processed_count = 0
        new_emails = 0
        
        for email_data in emails:
            try:
                # Check if email already exists
                existing_email = db_session.query(Email).filter(
                    Email.gmail_id == email_data.get("id")
                ).first()
                
                if existing_email:
                    # Update existing email if needed
                    if existing_email.updated_at < datetime.utcnow() - timedelta(hours=1):
                        _update_email(existing_email, email_data, db_session)
                        processed_count += 1
                    continue
                
                # Create new email record
                email = _create_email_record(email_data, db_session)
                if email:
                    new_emails += 1
                    processed_count += 1
                    
                    # Process email with AI if it meets criteria
                    if _should_process_email(email_data):
                        _process_email_ai(email, email_data)
                
            except Exception as e:
                logger.error(f"Error processing email {email_data.get('id')}: {e}")
                continue
        
        db_session.close()
        
        result = {
            "status": "completed",
            "processed_count": processed_count,
            "new_emails": new_emails,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Email sync completed: {processed_count} processed, {new_emails} new")
        return result
        
    except Exception as e:
        logger.error(f"Email sync failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.email_tasks.process_email")
def process_email(self, email_id: str, user_id: str) -> Dict[str, Any]:
    """Process a specific email with AI."""
    try:
        logger.info(f"Processing email {email_id} for user {user_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "processing"})
        
        db_session = get_db_session()
        
        # Get email
        email = db_session.query(Email).filter(Email.id == email_id).first()
        if not email:
            raise ValueError(f"Email {email_id} not found")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="email_processing",
            trigger_user=user_id,
            trigger_content=f"Email: {email.subject}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Process with AI
        ai_chain = get_ai_chain()
        result = ai_chain.process_email(
            email_data={
                "subject": email.subject,
                "body": email.body,
                "from": email.sender,
                "to": email.recipients,
                "date": email.received_at.isoformat()
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
            "email_id": email_id,
            "workflow_id": workflow_exec.id,
            "ai_result": result
        }
        
    except Exception as e:
        logger.error(f"Email processing failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.email_tasks.send_email")
def send_email(self, to: str, subject: str, body: str, user_id: str) -> Dict[str, Any]:
    """Send an email in the background."""
    try:
        logger.info(f"Sending email to {to}: {subject}")
        current_task.update_state(state="PROGRESS", meta={"status": "sending"})
        
        gmail_client = get_gmail_client()
        
        # Send email
        result = gmail_client.send_email(to, subject, body)
        
        # Store in database
        db_session = get_db_session()
        
        email = Email(
            subject=subject,
            body=body,
            sender=user_id,
            recipients=to,
            direction="outbound",
            status="sent",
            sent_at=datetime.utcnow(),
            gmail_id=result.get("id") if result else None
        )
        db_session.add(email)
        db_session.commit()
        db_session.close()
        
        return {
            "status": "sent",
            "email_id": email.id,
            "gmail_id": result.get("id") if result else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Email sending failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.email_tasks.analyze_email_thread")
def analyze_email_thread(self, thread_id: str, user_id: str) -> Dict[str, Any]:
    """Analyze an email thread for insights and actions."""
    try:
        logger.info(f"Analyzing email thread {thread_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "analyzing"})
        
        gmail_client = get_gmail_client()
        db_session = get_db_session()
        
        # Get thread emails
        thread_emails = gmail_client.get_thread_emails(thread_id)
        
        if not thread_emails:
            return {"status": "no_emails", "thread_id": thread_id}
        
        # Analyze thread content
        thread_content = "\n\n".join([
            f"From: {email.get('from', 'Unknown')}\nSubject: {email.get('subject', 'No subject')}\n\n{email.get('body', '')}"
            for email in thread_emails
        ])
        
        # Process with AI for analysis
        ai_chain = get_ai_chain()
        analysis = ai_chain.process_email(
            email_data={
                "subject": f"Thread Analysis: {thread_emails[0].get('subject', 'No subject')}",
                "body": thread_content,
                "from": "system",
                "to": user_id,
                "thread_id": thread_id
            },
            user_id=user_id
        )
        
        # Store analysis result
        # TODO: Create a dedicated table for thread analysis results
        
        db_session.close()
        
        return {
            "status": "completed",
            "thread_id": thread_id,
            "email_count": len(thread_emails),
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Thread analysis failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.email_tasks.cleanup_old_emails")
def cleanup_old_emails(self, days_old: int = 90) -> Dict[str, Any]:
    """Clean up old emails from the database."""
    try:
        logger.info(f"Cleaning up emails older than {days_old} days")
        current_task.update_state(state="PROGRESS", meta={"status": "cleaning"})
        
        db_session = get_db_session()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Count emails to be deleted
        old_emails_count = db_session.query(Email).filter(
            Email.received_at < cutoff_date
        ).count()
        
        # Delete old emails
        deleted_count = db_session.query(Email).filter(
            Email.received_at < cutoff_date
        ).delete()
        
        db_session.commit()
        db_session.close()
        
        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "old_emails_count": old_emails_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Email cleanup failed: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


# Helper functions
def _create_email_record(email_data: Dict[str, Any], db_session) -> Optional[Email]:
    """Create a new email record in the database."""
    try:
        # Create email record
        email = Email(
            gmail_id=email_data.get("id"),
            subject=email_data.get("subject", "No subject"),
            body=email_data.get("body", ""),
            sender=email_data.get("from", "Unknown"),
            recipients=email_data.get("to", ""),
            direction="inbound",
            status="received",
            received_at=email_data.get("date") or datetime.utcnow(),
            thread_id=email_data.get("threadId"),
            labels=email_data.get("labels", []),
            metadata=email_data
        )
        
        db_session.add(email)
        db_session.commit()
        
        # Process attachments if any
        if email_data.get("attachments"):
            _process_attachments(email, email_data["attachments"], db_session)
        
        return email
        
    except Exception as e:
        logger.error(f"Error creating email record: {e}")
        db_session.rollback()
        return None


def _update_email(email: Email, email_data: Dict[str, Any], db_session) -> None:
    """Update an existing email record."""
    try:
        email.subject = email_data.get("subject", email.subject)
        email.body = email_data.get("body", email.body)
        email.labels = email_data.get("labels", email.labels)
        email.metadata = email_data
        email.updated_at = datetime.utcnow()
        
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error updating email: {e}")
        db_session.rollback()


def _process_attachments(email: Email, attachments: List[Dict[str, Any]], db_session) -> None:
    """Process email attachments."""
    try:
        for attachment_data in attachments:
            attachment = EmailAttachment(
                email_id=email.id,
                filename=attachment_data.get("filename", "unknown"),
                content_type=attachment_data.get("contentType", "application/octet-stream"),
                size=attachment_data.get("size", 0),
                gmail_attachment_id=attachment_data.get("id"),
                metadata=attachment_data
            )
            db_session.add(attachment)
        
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Error processing attachments: {e}")
        db_session.rollback()


def _should_process_email(email_data: Dict[str, Any]) -> bool:
    """Determine if an email should be processed with AI."""
    # Process emails that:
    # 1. Are not from the user themselves
    # 2. Have substantial content
    # 3. Are not automated/notification emails
    
    subject = email_data.get("subject", "").lower()
    body = email_data.get("body", "")
    
    # Skip automated emails
    auto_keywords = ["notification", "alert", "system", "automated", "do not reply"]
    if any(keyword in subject for keyword in auto_keywords):
        return False
    
    # Skip emails with minimal content
    if len(body.strip()) < 50:
        return False
    
    # Skip emails from common notification addresses
    sender = email_data.get("from", "").lower()
    if any(domain in sender for domain in ["noreply", "no-reply", "notifications"]):
        return False
    
    return True


def _process_email_ai(email: Email, email_data: Dict[str, Any]) -> None:
    """Process email with AI for initial analysis."""
    try:
        # Queue AI processing task
        process_email.delay(
            email_id=str(email.id),
            user_id=email_data.get("to", "system")
        )
        
    except Exception as e:
        logger.error(f"Error queuing email AI processing: {e}") 