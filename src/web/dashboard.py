"""Modern web dashboard for Reflex Executive Assistant SaaS platform."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json

from src.auth.dependencies import get_current_user
from src.storage.db import get_db_session
from src.storage.models import User, Conversation, WorkflowExecution
from src.ai.chain import ReflexAIChain
from src.kb.seeder import KnowledgeBaseSeeder

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Main dashboard homepage."""
    
    # Get user's recent activity
    recent_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).limit(5).all()
    
    recent_workflows = db.query(WorkflowExecution).filter(
        WorkflowExecution.trigger_user == current_user.id
    ).order_by(WorkflowExecution.created_at.desc()).limit(5).all()
    
    # Get quick stats
    total_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()
    
    total_workflows = db.query(WorkflowExecution).filter(
        WorkflowExecution.trigger_user == current_user.id
    ).count()
    
    # Get platform-specific stats
    slack_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.platform == "slack"
    ).count()
    
    email_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.platform == "email"
    ).count()
    
    asana_workflows = db.query(WorkflowExecution).filter(
        WorkflowExecution.trigger_user == current_user.id,
        WorkflowExecution.workflow_type == "asana_update"
    ).count()
    
    context = {
        "request": request,
        "user": current_user,
        "recent_conversations": recent_conversations,
        "recent_workflows": recent_workflows,
        "stats": {
            "total_conversations": total_conversations,
            "total_workflows": total_workflows,
            "slack_conversations": slack_conversations,
            "email_conversations": email_conversations,
            "asana_workflows": asana_workflows
        }
    }
    
    return templates.TemplateResponse("dashboard/home.html", context)


@router.get("/conversations", response_class=HTMLResponse)
async def conversations_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Conversations management page."""
    
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()
    
    context = {
        "request": request,
        "user": current_user,
        "conversations": conversations
    }
    
    return templates.TemplateResponse("dashboard/conversations.html", context)


@router.get("/conversations/{conversation_id}", response_class=HTMLResponse)
async def conversation_detail(
    conversation_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Individual conversation detail page."""
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages for this conversation
    messages = conversation.messages.order_by(Conversation.timestamp.asc()).all()
    
    context = {
        "request": request,
        "user": current_user,
        "conversation": conversation,
        "messages": messages
    }
    
    return templates.TemplateResponse("dashboard/conversation_detail.html", context)


@router.get("/workflows", response_class=HTMLResponse)
async def workflows_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Workflows management page."""
    
    workflows = db.query(WorkflowExecution).filter(
        WorkflowExecution.trigger_user == current_user.id
    ).order_by(WorkflowExecution.created_at.desc()).all()
    
    context = {
        "request": request,
        "user": current_user,
        "workflows": workflows
    }
    
    return templates.TemplateResponse("dashboard/workflows.html", context)


@router.get("/integrations", response_class=HTMLResponse)
async def integrations_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Integrations setup page."""
    
    context = {
        "request": request,
        "user": current_user,
        "integrations": {
            "slack": {
                "name": "Slack",
                "description": "Connect your Slack workspace for real-time AI assistance",
                "status": "connected" if current_user.slack_workspace_id else "not_connected",
                "icon": "slack",
                "color": "#4A154B"
            },
            "gmail": {
                "name": "Gmail",
                "description": "Connect your Gmail account for email processing and automation",
                "status": "connected" if current_user.gmail_connected else "not_connected",
                "icon": "gmail",
                "color": "#EA4335"
            },
            "asana": {
                "name": "Asana",
                "description": "Connect your Asana workspace for project management automation",
                "status": "connected" if current_user.asana_workspace_id else "not_connected",
                "icon": "asana",
                "color": "#F06A6A"
            }
        }
    }
    
    return templates.TemplateResponse("dashboard/integrations.html", context)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """User settings page."""
    
    context = {
        "request": request,
        "user": current_user
    }
    
    return templates.TemplateResponse("dashboard/settings.html", context)


@router.get("/help", response_class=HTMLResponse)
async def help_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Help and documentation page."""
    
    context = {
        "request": request,
        "user": current_user,
        "faqs": [
            {
                "question": "How do I connect my Slack workspace?",
                "answer": "Go to the Integrations page and click 'Connect' next to Slack. Follow the authorization process to connect your workspace."
            },
            {
                "question": "Can the AI help with email management?",
                "answer": "Yes! Connect your Gmail account and the AI will automatically process emails, create tasks, and respond to common inquiries."
            },
            {
                "question": "How do I customize the AI's responses?",
                "answer": "Visit the Settings page to configure your preferences, company context, and response style."
            },
            {
                "question": "What types of tasks can the AI automate?",
                "answer": "The AI can schedule meetings, create Asana tasks, draft emails, answer questions, and manage your workflow across multiple platforms."
            },
            {
                "question": "Is my data secure?",
                "answer": "Absolutely! We use enterprise-grade security with encryption, secure API connections, and strict data privacy controls."
            }
        ]
    }
    
    return templates.TemplateResponse("dashboard/help.html", context)


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Analytics and insights page."""
    
    # Get analytics data
    total_conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()
    
    platform_breakdown = db.query(Conversation.platform, db.func.count(Conversation.id)).filter(
        Conversation.user_id == current_user.id
    ).group_by(Conversation.platform).all()
    
    workflow_types = db.query(WorkflowExecution.workflow_type, db.func.count(WorkflowExecution.id)).filter(
        WorkflowExecution.trigger_user == current_user.id
    ).group_by(WorkflowExecution.workflow_type).all()
    
    context = {
        "request": request,
        "user": current_user,
        "analytics": {
            "total_conversations": total_conversations,
            "platform_breakdown": dict(platform_breakdown),
            "workflow_types": dict(workflow_types)
        }
    }
    
    return templates.TemplateResponse("dashboard/analytics.html", context)


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Onboarding wizard for new users."""
    
    context = {
        "request": request,
        "user": current_user,
        "steps": [
            {
                "id": 1,
                "title": "Welcome to Reflex",
                "description": "Let's get you set up with your AI assistant",
                "completed": True
            },
            {
                "id": 2,
                "title": "Connect Your Tools",
                "description": "Connect Slack, Gmail, and Asana for seamless integration",
                "completed": bool(current_user.slack_workspace_id or current_user.gmail_connected or current_user.asana_workspace_id)
            },
            {
                "id": 3,
                "title": "Customize Settings",
                "description": "Configure your preferences and company context",
                "completed": bool(current_user.company_name and current_user.role)
            },
            {
                "id": 4,
                "title": "Test Your Assistant",
                "description": "Try out your AI assistant with a test conversation",
                "completed": False
            }
        ]
    }
    
    return templates.TemplateResponse("dashboard/onboarding.html", context) 