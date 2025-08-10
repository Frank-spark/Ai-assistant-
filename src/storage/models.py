"""Database models for Reflex Executive Assistant."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

Base = declarative_base()


class User(Base):
    """User model for authentication and permissions."""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="approver")
    webhook_events: Mapped[List["WebhookEvent"]] = relationship("WebhookEvent", back_populates="user")
    
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
    )


class WebhookEvent(Base):
    """Model for tracking webhook events from external services."""
    __tablename__ = "webhook_events"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # slack, gmail, asana
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="webhook_events")
    
    __table_args__ = (
        Index("idx_webhook_events_source", "source"),
        Index("idx_webhook_events_type", "event_type"),
        Index("idx_webhook_events_processed", "processed"),
        Index("idx_webhook_events_created", "created_at"),
        UniqueConstraint("source", "event_id", name="uq_webhook_source_event"),
    )


class Approval(Base):
    """Model for human-in-the-loop approvals."""
    __tablename__ = "approvals"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # email, slack, asana
    action_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)  # pending, approved, rejected
    requester_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", index=True)  # low, normal, high, urgent
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approver_id], back_populates="approvals")
    
    __table_args__ = (
        Index("idx_approvals_type", "action_type"),
        Index("idx_approvals_status", "status"),
        Index("idx_approvals_priority", "priority"),
        Index("idx_approvals_requested", "requested_at"),
        Index("idx_approvals_expires", "expires_at"),
    )


class KnowledgeBaseDocument(Base):
    """Model for storing knowledge base documents and their embeddings."""
    __tablename__ = "knowledge_base_documents"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # markdown, pdf, docx, etc.
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # company_docs, emails, meetings, etc.
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Pinecone vector ID
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_kb_docs_title", "title"),
        Index("idx_kb_docs_content_type", "content_type"),
        Index("idx_kb_docs_source", "source"),
        Index("idx_kb_docs_tags", "tags", postgresql_using="gin"),
        Index("idx_kb_docs_embedding", "embedding_id"),
        Index("idx_kb_docs_created", "created_at"),
    )


class EmailThread(Base):
    """Model for tracking email threads and conversations."""
    __tablename__ = "email_threads"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)  # Gmail thread ID
    subject: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    participants: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)  # active, archived, resolved
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    messages: Mapped[List["EmailMessage"]] = relationship("EmailMessage", back_populates="thread")
    
    __table_args__ = (
        Index("idx_email_threads_subject", "subject"),
        Index("idx_email_threads_status", "status"),
        Index("idx_email_threads_priority", "priority"),
        Index("idx_email_threads_last_message", "last_message_at"),
        Index("idx_email_threads_tags", "tags", postgresql_using="gin"),
    )


class EmailMessage(Base):
    """Model for individual email messages within threads."""
    __tablename__ = "email_messages"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)  # Gmail message ID
    thread_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("email_threads.id"), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recipients: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    cc: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    bcc: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_plain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    labels: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Relationships
    thread: Mapped["EmailThread"] = relationship("EmailThread", back_populates="messages")
    
    __table_args__ = (
        Index("idx_email_messages_sender", "sender"),
        Index("idx_email_messages_subject", "subject"),
        Index("idx_email_messages_sent", "sent_at"),
        Index("idx_email_messages_received", "received_at"),
        Index("idx_email_messages_labels", "labels", postgresql_using="gin"),
        Index("idx_email_messages_read", "is_read"),
    )


class SlackChannel(Base):
    """Model for tracking Slack channels and their state."""
    __tablename__ = "slack_channels"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)  # Slack channel ID
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    messages: Mapped[List["SlackMessage"]] = relationship("SlackMessage", back_populates="channel")
    
    __table_args__ = (
        Index("idx_slack_channels_name", "name"),
        Index("idx_slack_channels_private", "is_private"),
        Index("idx_slack_channels_archived", "is_archived"),
    )


class SlackMessage(Base):
    """Model for tracking Slack messages."""
    __tablename__ = "slack_messages"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)  # Slack message timestamp
    channel_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("slack_channels.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # Slack user ID
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    thread_ts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    parent_user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attachments: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    reactions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)
    
    # Relationships
    channel: Mapped["SlackChannel"] = relationship("SlackChannel", back_populates="messages")
    
    __table_args__ = (
        Index("idx_slack_messages_user", "user_id"),
        Index("idx_slack_messages_thread", "thread_ts"),
        Index("idx_slack_messages_sent", "sent_at"),
        Index("idx_slack_messages_bot", "is_bot"),
    )


class AsanaTask(Base):
    """Model for tracking Asana tasks."""
    __tablename__ = "asana_tasks"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)  # Asana task ID
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    section_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    assignee_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    due_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # HH:MM format
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal", index=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    custom_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_asana_tasks_name", "name"),
        Index("idx_asana_tasks_project", "project_id"),
        Index("idx_asana_tasks_assignee", "assignee_id"),
        Index("idx_asana_tasks_due", "due_date"),
        Index("idx_asana_tasks_status", "status"),
        Index("idx_asana_tasks_priority", "priority"),
        Index("idx_asana_tasks_tags", "tags", postgresql_using="gin"),
    )


class Meeting(Base):
    """Model for tracking meetings and their outcomes."""
    __tablename__ = "meetings"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attendees: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    organizer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meeting_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 1:1, team, client, etc.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled", index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    agenda: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    decisions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_meetings_title", "title"),
        Index("idx_meetings_start", "start_time"),
        Index("idx_meetings_organizer", "organizer"),
        Index("idx_meetings_type", "meeting_type"),
        Index("idx_meetings_status", "status"),
        Index("idx_meetings_follow_up", "follow_up_required"),
    )


class MeetingTranscript(Base):
    """Model for storing meeting transcripts."""
    __tablename__ = "meeting_transcripts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=False, index=True)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speaker_diarization: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="transcripts")


class MeetingAnalysis(Base):
    """Model for storing AI analysis of meetings."""
    __tablename__ = "meeting_analyses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("meetings.id"), nullable=False, index=True)
    analysis_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decisions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low, medium, high
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="analyses")


class WorkflowExecution(Base):
    """Model for tracking workflow executions."""
    __tablename__ = "workflow_executions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # webhook, scheduled, manual
    trigger_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", index=True)  # running, completed, failed, cancelled
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    steps_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)
    
    __table_args__ = (
        Index("idx_workflow_executions_name", "workflow_name"),
        Index("idx_workflow_executions_trigger", "trigger_type"),
        Index("idx_workflow_executions_status", "status"),
        Index("idx_workflow_executions_started", "started_at"),
        Index("idx_workflow_executions_completed", "completed_at"),
    ) 


class Decision(Base):
    """Model for tracking executive decisions."""
    __tablename__ = "decisions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    requester: Mapped[str] = mapped_column(String(255), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)  # APPROVE, REJECT, REVIEW
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    risk_assessment: Mapped[str] = mapped_column(String(20), nullable=False)  # Low, Medium, High
    business_impact: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    compliance_check: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    auto_approval_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_approvals: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, approved, rejected
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class DecisionContext(Base):
    """Model for storing decision context and business metrics."""
    __tablename__ = "decision_contexts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)  # performance, goals, budget, risk, etc.
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    decision: Mapped["Decision"] = relationship("Decision", back_populates="contexts")


class BusinessMetrics(Base):
    """Model for storing business metrics used in decision making."""
    __tablename__ = "business_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(20), nullable=True)
    metric_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # financial, operational, customer, etc.
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # system, manual, integration
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# Add relationships to Decision model
Decision.contexts: Mapped[List["DecisionContext"]] = relationship("DecisionContext", back_populates="decision")


class StrategicContext(Base):
    """Model for tracking strategic context injections."""
    __tablename__ = "strategic_contexts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    context_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    injected_content: Mapped[str] = mapped_column(Text, nullable=False)
    final_content: Mapped[str] = mapped_column(Text, nullable=False)
    alignment_score: Mapped[float] = mapped_column(Float, nullable=False)
    cultural_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CompanyValues(Base):
    """Model for storing company values and cultural principles."""
    __tablename__ = "company_values"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value_description: Mapped[str] = mapped_column(Text, nullable=False)
    value_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # core, cultural, operational
    priority_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TeamAlignment(Base):
    """Model for tracking team alignment with strategic goals."""
    __tablename__ = "team_alignments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    goal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alignment_score: Mapped[float] = mapped_column(Float, nullable=False)
    progress_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_assessment: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_assessment: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CulturalMetrics(Base):
    """Model for tracking cultural health metrics."""
    __tablename__ = "cultural_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # engagement, satisfaction, well_being, diversity
    team_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # survey, system, manual
    trend: Mapped[str] = mapped_column(String(20), nullable=False, default="stable")  # improving, declining, stable
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)) 