"""SaaS models for user management, subscriptions, and billing."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import enum

from src.storage.models import Base


class SubscriptionStatus(enum.Enum):
    """Subscription status enumeration."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"
    PAST_DUE = "past_due"


class PlanType(enum.Enum):
    """Subscription plan types."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class User(Base):
    """Extended user model for SaaS platform."""
    __tablename__ = "saas_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company_name = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    
    # Subscription info
    subscription_status = Column(String(50), default=SubscriptionStatus.TRIAL.value)
    plan_type = Column(String(50), default=PlanType.FREE.value)
    trial_ends_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    subscription_ends_at = Column(DateTime, nullable=True)
    
    # Integration connections
    slack_workspace_id = Column(String(255), nullable=True)
    slack_workspace_name = Column(String(255), nullable=True)
    gmail_connected = Column(Boolean, default=False)
    gmail_email = Column(String(255), nullable=True)
    asana_workspace_id = Column(String(255), nullable=True)
    asana_workspace_name = Column(String(255), nullable=True)
    
    # Preferences
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    notification_preferences = Column(JSON, default=dict)
    
    # Usage tracking
    monthly_conversations = Column(Integer, default=0)
    monthly_workflows = Column(Integer, default=0)
    last_activity_at = Column(DateTime, default=func.now())
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    billing_history = relationship("BillingHistory", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")


class Subscription(Base):
    """Subscription model for billing and plan management."""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    
    # Plan details
    plan_type = Column(String(50), nullable=False)
    plan_name = Column(String(100), nullable=False)
    plan_description = Column(Text, nullable=True)
    
    # Billing details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly
    
    # Status and dates
    status = Column(String(50), default=SubscriptionStatus.ACTIVE.value)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # External billing provider
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    
    # Features and limits
    features = Column(JSON, default=dict)
    limits = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    billing_history = relationship("BillingHistory", back_populates="subscription")


class BillingHistory(Base):
    """Billing history for tracking payments and invoices."""
    __tablename__ = "billing_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(String(50), nullable=False)  # paid, pending, failed, refunded
    
    # Invoice details
    invoice_number = Column(String(100), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    # Billing period
    billing_period_start = Column(DateTime, nullable=True)
    billing_period_end = Column(DateTime, nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="billing_history")
    subscription = relationship("Subscription", back_populates="billing_history")


class UsageLog(Base):
    """Usage tracking for conversations, workflows, and API calls."""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    
    # Usage details
    usage_type = Column(String(50), nullable=False)  # conversation, workflow, api_call
    resource_id = Column(String(255), nullable=True)  # conversation_id, workflow_id, etc.
    platform = Column(String(50), nullable=True)  # slack, email, asana, api
    
    # Metrics
    tokens_used = Column(Integer, default=0)
    api_calls = Column(Integer, default=1)
    duration_seconds = Column(Float, default=0.0)
    
    # Cost tracking
    estimated_cost = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")


class APIKey(Base):
    """API keys for external integrations and API access."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    
    # Key details
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(8), nullable=False)  # First 8 characters for display
    
    # Permissions
    permissions = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys")


class Team(Base):
    """Team model for multi-user organizations."""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Team settings
    owner_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Billing
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    
    # Settings
    settings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TeamMember(Base):
    """Team membership model."""
    __tablename__ = "team_members"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    
    # Role and permissions
    role = Column(String(50), default="member")  # owner, admin, member
    permissions = Column(JSON, default=list)
    
    # Status
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=func.now())
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Invitation(Base):
    """Team invitation model."""
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    invited_by_id = Column(Integer, ForeignKey("saas_users.id"), nullable=False)
    
    # Invitation details
    email = Column(String(255), nullable=False)
    role = Column(String(50), default="member")
    token = Column(String(255), unique=True, nullable=False)
    
    # Status
    is_accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) 