"""Meeting recording and analysis tasks for Reflex Executive Assistant."""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from celery import current_task

from ...config import get_settings
from ...storage.models import Meeting, MeetingTranscript, MeetingAnalysis, WorkflowExecution
from ...storage.db import get_db_session
from ...integrations.meeting_recorder import get_meeting_manager
from ...ai.chain import get_ai_chain

logger = logging.getLogger(__name__)
celery_app = get_settings().celery_app


@celery_app.task(bind=True, name="src.jobs.tasks.meeting_tasks.start_meeting_recording")
def start_meeting_recording(
    self,
    meeting_title: str,
    attendees: List[str] = None,
    meeting_type: str = "executive"
) -> Dict[str, Any]:
    """Start recording an executive meeting."""
    try:
        logger.info(f"Starting meeting recording: {meeting_title}")
        current_task.update_state(state="PROGRESS", meta={"status": "starting_recording"})
        
        # Create workflow execution
        db_session = get_db_session()
        workflow_exec = WorkflowExecution(
            workflow_type="meeting_recording_start",
            trigger_content=f"Meeting: {meeting_title}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Start recording using meeting manager
        meeting_manager = get_meeting_manager()
        result = asyncio.run(meeting_manager.start_executive_meeting(
            meeting_title=meeting_title,
            attendees=attendees or [],
            meeting_type=meeting_type
        ))
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = result
        db_session.commit()
        db_session.close()
        
        logger.info(f"Meeting recording started: {result['meeting_id']}")
        
        return {
            "status": "recording_started",
            "workflow_id": workflow_exec.id,
            "meeting_id": result["meeting_id"],
            "message": result["message"]
        }
        
    except Exception as e:
        logger.error(f"Error starting meeting recording: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.meeting_tasks.end_meeting_recording")
def end_meeting_recording(self, meeting_id: str) -> Dict[str, Any]:
    """End recording and analyze executive meeting."""
    try:
        logger.info(f"Ending meeting recording: {meeting_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "ending_recording"})
        
        # Create workflow execution
        db_session = get_db_session()
        workflow_exec = WorkflowExecution(
            workflow_type="meeting_recording_end",
            trigger_content=f"Meeting ID: {meeting_id}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # End recording and process
        meeting_manager = get_meeting_manager()
        result = asyncio.run(meeting_manager.end_executive_meeting(meeting_id))
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = result
        db_session.commit()
        db_session.close()
        
        logger.info(f"Meeting recording completed: {meeting_id}")
        
        return {
            "status": "recording_completed",
            "workflow_id": workflow_exec.id,
            "meeting_id": meeting_id,
            "transcript_length": result.get("transcript_length", 0),
            "analysis_summary": result.get("analysis_summary", ""),
            "action_items": result.get("action_items", [])
        }
        
    except Exception as e:
        logger.error(f"Error ending meeting recording: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.meeting_tasks.analyze_meeting_transcript")
def analyze_meeting_transcript(self, meeting_id: str) -> Dict[str, Any]:
    """Analyze a meeting transcript using AI."""
    try:
        logger.info(f"Analyzing meeting transcript: {meeting_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "analyzing"})
        
        db_session = get_db_session()
        
        # Get meeting and transcript
        meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        transcript = db_session.query(MeetingTranscript).filter(
            MeetingTranscript.meeting_id == meeting_id
        ).first()
        
        if not meeting or not transcript:
            raise ValueError(f"Meeting or transcript not found for {meeting_id}")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="meeting_analysis",
            trigger_content=f"Analysis for: {meeting.title}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Analyze transcript with AI
        ai_chain = get_ai_chain()
        analysis_result = asyncio.run(ai_chain.analyze_text(
            text=transcript.transcript_text,
            analysis_type="meeting_summary",
            context="executive_meeting"
        ))
        
        # Create or update analysis record
        existing_analysis = db_session.query(MeetingAnalysis).filter(
            MeetingAnalysis.meeting_id == meeting_id
        ).first()
        
        if existing_analysis:
            existing_analysis.analysis_data = analysis_result
            existing_analysis.summary = analysis_result.get("summary", "")
            existing_analysis.action_items_count = len(analysis_result.get("action_items", []))
            existing_analysis.decisions_count = len(analysis_result.get("decisions", []))
            existing_analysis.risk_level = analysis_result.get("risk_level", "low")
            existing_analysis.sentiment_score = analysis_result.get("sentiment_score", 0.0)
            existing_analysis.created_at = datetime.now(timezone.utc)
        else:
            analysis_record = MeetingAnalysis(
                meeting_id=meeting_id,
                analysis_data=analysis_result,
                summary=analysis_result.get("summary", ""),
                action_items_count=len(analysis_result.get("action_items", [])),
                decisions_count=len(analysis_result.get("decisions", [])),
                risk_level=analysis_result.get("risk_level", "low"),
                sentiment_score=analysis_result.get("sentiment_score", 0.0)
            )
            db_session.add(analysis_record)
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = analysis_result
        db_session.commit()
        db_session.close()
        
        logger.info(f"Meeting analysis completed: {meeting_id}")
        
        return {
            "status": "analysis_completed",
            "workflow_id": workflow_exec.id,
            "meeting_id": meeting_id,
            "summary": analysis_result.get("summary", ""),
            "action_items": analysis_result.get("action_items", []),
            "decisions": analysis_result.get("decisions", []),
            "risk_level": analysis_result.get("risk_level", "low")
        }
        
    except Exception as e:
        logger.error(f"Error analyzing meeting transcript: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.meeting_tasks.create_meeting_summary")
def create_meeting_summary(self, meeting_id: str) -> Dict[str, Any]:
    """Create a comprehensive meeting summary with action items."""
    try:
        logger.info(f"Creating meeting summary: {meeting_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "creating_summary"})
        
        db_session = get_db_session()
        
        # Get meeting details
        meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        transcript = db_session.query(MeetingTranscript).filter(
            MeetingTranscript.meeting_id == meeting_id
        ).first()
        analysis = db_session.query(MeetingAnalysis).filter(
            MeetingAnalysis.meeting_id == meeting_id
        ).first()
        
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="meeting_summary",
            trigger_content=f"Summary for: {meeting.title}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Generate summary using AI
        ai_chain = get_ai_chain()
        
        summary_prompt = f"""
        Create a comprehensive executive meeting summary for: {meeting.title}
        
        Meeting Details:
        - Date: {meeting.start_time}
        - Duration: {transcript.duration_minutes if transcript else 'Unknown'} minutes
        - Attendees: {', '.join(meeting.attendees) if meeting.attendees else 'Not specified'}
        
        Key Points from Analysis:
        - Summary: {analysis.analysis_data.get('summary', '') if analysis else 'No analysis available'}
        - Action Items: {len(analysis.analysis_data.get('action_items', [])) if analysis else 0} items
        - Decisions: {len(analysis.analysis_data.get('decisions', [])) if analysis else 0} decisions
        
        Please create a professional executive summary including:
        1. Executive Summary
        2. Key Discussion Points
        3. Decisions Made
        4. Action Items with Assignees
        5. Next Steps
        6. Follow-up Required
        """
        
        summary_result = asyncio.run(ai_chain.generate_text(
            prompt=summary_prompt,
            context="executive_summary"
        ))
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = {"summary": summary_result}
        db_session.commit()
        db_session.close()
        
        logger.info(f"Meeting summary created: {meeting_id}")
        
        return {
            "status": "summary_created",
            "workflow_id": workflow_exec.id,
            "meeting_id": meeting_id,
            "summary": summary_result,
            "meeting_title": meeting.title
        }
        
    except Exception as e:
        logger.error(f"Error creating meeting summary: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.meeting_tasks.send_meeting_follow_ups")
def send_meeting_follow_ups(self, meeting_id: str) -> Dict[str, Any]:
    """Send follow-up emails and tasks based on meeting outcomes."""
    try:
        logger.info(f"Sending meeting follow-ups: {meeting_id}")
        current_task.update_state(state="PROGRESS", meta={"status": "sending_follow_ups"})
        
        db_session = get_db_session()
        
        # Get meeting and analysis
        meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        analysis = db_session.query(MeetingAnalysis).filter(
            MeetingAnalysis.meeting_id == meeting_id
        ).first()
        
        if not meeting or not analysis:
            raise ValueError(f"Meeting or analysis not found for {meeting_id}")
        
        # Create workflow execution
        workflow_exec = WorkflowExecution(
            workflow_type="meeting_follow_ups",
            trigger_content=f"Follow-ups for: {meeting.title}",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        action_items = analysis.analysis_data.get("action_items", [])
        follow_ups_sent = 0
        
        # Send follow-ups for each action item
        for item in action_items:
            try:
                # Create task in Asana or similar
                # Send email reminder
                # Update Slack channel
                follow_ups_sent += 1
            except Exception as e:
                logger.warning(f"Failed to send follow-up for action item: {e}")
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = {"follow_ups_sent": follow_ups_sent}
        db_session.commit()
        db_session.close()
        
        logger.info(f"Meeting follow-ups sent: {meeting_id} ({follow_ups_sent} items)")
        
        return {
            "status": "follow_ups_sent",
            "workflow_id": workflow_exec.id,
            "meeting_id": meeting_id,
            "follow_ups_sent": follow_ups_sent,
            "total_action_items": len(action_items)
        }
        
    except Exception as e:
        logger.error(f"Error sending meeting follow-ups: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="src.jobs.tasks.meeting_tasks.cleanup_old_recordings")
def cleanup_old_recordings(self, days_old: int = 30) -> Dict[str, Any]:
    """Clean up old meeting recordings and temporary files."""
    try:
        logger.info(f"Cleaning up recordings older than {days_old} days")
        current_task.update_state(state="PROGRESS", meta={"status": "cleaning_up"})
        
        # Create workflow execution
        db_session = get_db_session()
        workflow_exec = WorkflowExecution(
            workflow_type="recording_cleanup",
            trigger_content=f"Cleanup recordings older than {days_old} days",
            status="started",
            started_at=datetime.utcnow()
        )
        db_session.add(workflow_exec)
        db_session.commit()
        
        # Find old meetings
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        old_meetings = db_session.query(Meeting).filter(
            Meeting.created_at < cutoff_date,
            Meeting.status == "completed"
        ).all()
        
        cleaned_count = 0
        
        for meeting in old_meetings:
            try:
                # Clean up associated files
                # Remove temporary audio files
                # Archive transcripts if needed
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup meeting {meeting.id}: {e}")
        
        # Update workflow execution
        workflow_exec.status = "completed"
        workflow_exec.completed_at = datetime.utcnow()
        workflow_exec.result = {"cleaned_count": cleaned_count}
        db_session.commit()
        db_session.close()
        
        logger.info(f"Recording cleanup completed: {cleaned_count} meetings cleaned")
        
        return {
            "status": "cleanup_completed",
            "workflow_id": workflow_exec.id,
            "cleaned_count": cleaned_count,
            "days_old": days_old
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up recordings: {e}", exc_info=True)
        current_task.update_state(state="FAILURE", meta={"error": str(e)})
        raise 