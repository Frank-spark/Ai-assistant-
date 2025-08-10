"""Demo landing page and sandbox for Reflex AI Assistant."""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json
import uuid

from src.storage.db import get_db_session
from src.storage.models import User, Conversation, WorkflowExecution
from src.auth.dependencies import get_current_user_optional

router = APIRouter(prefix="/demo", tags=["demo"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/", response_class=HTMLResponse)
async def demo_landing(request: Request):
    """Demo landing page with live sandbox."""
    
    context = {
        "request": request,
        "demo_features": [
            {
                "title": "Voice-First Leadership",
                "description": "Speak naturally to your AI assistant",
                "icon": "🎤",
                "demo_url": "/demo/voice"
            },
            {
                "title": "Strategic Dashboard",
                "description": "Real-time KPIs and organizational insights",
                "icon": "📊",
                "demo_url": "/demo/dashboard"
            },
            {
                "title": "Team Alignment",
                "description": "Keep everyone focused on your vision",
                "icon": "👥",
                "demo_url": "/demo/team"
            },
            {
                "title": "Workflow Automation",
                "description": "AI-powered task and project management",
                "icon": "⚡",
                "demo_url": "/demo/workflows"
            }
        ],
        "demo_stats": {
            "users": 4,
            "conversations": 12,
            "workflows": 8,
            "time_saved": "15 hours/week"
        }
    }
    
    return templates.TemplateResponse("demo/landing.html", context)


@router.get("/sandbox", response_class=HTMLResponse)
async def demo_sandbox(
    request: Request,
    db: Session = Depends(get_db_session)
):
    """Live demo sandbox with synthetic data."""
    
    # Get demo data
    demo_user = db.query(User).filter(User.email == "sarah@techflow.com").first()
    
    if not demo_user:
        # Create demo user if not exists
        demo_user = User(
            id="U123456",
            email="sarah@techflow.com",
            name="Sarah Chen",
            role="CEO",
            company_name="TechFlow Solutions",
            subscription_tier="professional",
            is_active=True
        )
        db.add(demo_user)
        db.commit()
    
    # Get recent conversations
    conversations = db.query(Conversation).filter(
        Conversation.user_id == demo_user.id
    ).order_by(Conversation.updated_at.desc()).limit(5).all()
    
    # Get recent workflows
    workflows = db.query(WorkflowExecution).filter(
        WorkflowExecution.trigger_user == demo_user.id
    ).order_by(WorkflowExecution.created_at.desc()).limit(5).all()
    
    # Demo metrics
    demo_metrics = {
        "emails_processed": 24,
        "tasks_created": 18,
        "meetings_scheduled": 6,
        "time_saved_hours": 15,
        "response_time_minutes": 2.3,
        "accuracy_percentage": 94.2
    }
    
    context = {
        "request": request,
        "user": demo_user,
        "conversations": conversations,
        "workflows": workflows,
        "metrics": demo_metrics,
        "demo_mode": True
    }
    
    return templates.TemplateResponse("demo/sandbox.html", context)


@router.get("/voice", response_class=HTMLResponse)
async def demo_voice(request: Request):
    """Voice interaction demo."""
    
    context = {
        "request": request,
        "voice_commands": [
            "Show me our Q4 performance against goals",
            "Create a task for John to review the budget",
            "Schedule a meeting with the marketing team",
            "Summarize yesterday's board meeting",
            "Check if we're on track with strategic goals",
            "Help me prepare for the investor presentation"
        ],
        "demo_responses": [
            {
                "command": "Show me our Q4 performance against goals",
                "response": "Based on your data, you're at 87% of Q4 targets. Sales team is ahead by 12%, but marketing is 8% behind. Would you like me to create an action plan?"
            },
            {
                "command": "Create a task for John to review the budget",
                "response": "I've created a task for John to review the Q4 budget. It's assigned to him with a due date of Friday. I'll send him a notification."
            },
            {
                "command": "Schedule a meeting with the marketing team",
                "response": "I've scheduled a meeting with the marketing team for tomorrow at 2 PM. I've sent calendar invites to Jen, Alex, and Mike. The agenda will focus on Q2 campaign planning."
            }
        ]
    }
    
    return templates.TemplateResponse("demo/voice.html", context)


@router.get("/dashboard", response_class=HTMLResponse)
async def demo_dashboard(request: Request):
    """Strategic dashboard demo."""
    
    # Demo KPIs
    kpis = {
        "revenue": {
            "current": "$2.1M",
            "target": "$2.5M",
            "percentage": 84,
            "trend": "up"
        },
        "customers": {
            "current": 156,
            "target": 200,
            "percentage": 78,
            "trend": "up"
        },
        "team_size": {
            "current": 45,
            "target": 50,
            "percentage": 90,
            "trend": "up"
        },
        "product_launches": {
            "current": 2,
            "target": 3,
            "percentage": 67,
            "trend": "neutral"
        }
    }
    
    # Demo organizational template progress
    template_progress = [
        {"section": "Leadership & Key Roles", "completed": True, "progress": 100},
        {"section": "Organizational Structure", "completed": True, "progress": 100},
        {"section": "Decision & Escalation Paths", "completed": True, "progress": 100},
        {"section": "Core Processes & Workflows", "completed": True, "progress": 100},
        {"section": "Performance Metrics (KPIs)", "completed": True, "progress": 100},
        {"section": "Strategic Goals & Vision", "completed": True, "progress": 100},
        {"section": "Values & Operating Principles", "completed": True, "progress": 100},
        {"section": "Products, Services & Technology", "completed": True, "progress": 100},
        {"section": "Risk, Compliance & Restrictions", "completed": False, "progress": 75},
        {"section": "AI Roles & Functions", "completed": False, "progress": 60},
        {"section": "Review & Update Cycle", "completed": False, "progress": 40}
    ]
    
    context = {
        "request": request,
        "kpis": kpis,
        "template_progress": template_progress,
        "demo_mode": True
    }
    
    return templates.TemplateResponse("demo/dashboard.html", context)


@router.get("/team", response_class=HTMLResponse)
async def demo_team(request: Request):
    """Team alignment demo."""
    
    # Demo team structure
    team = [
        {
            "name": "Sarah Chen",
            "role": "CEO",
            "department": "Executive",
            "goals": ["Series A funding", "Team scaling", "Market expansion"],
            "progress": 85,
            "avatar": "👩‍💼"
        },
        {
            "name": "Mike Rodriguez",
            "role": "CTO",
            "department": "Engineering",
            "goals": ["Voice recognition launch", "Hire 10 engineers", "Technical architecture"],
            "progress": 72,
            "avatar": "👨‍💻"
        },
        {
            "name": "Jennifer Park",
            "role": "Marketing Director",
            "department": "Marketing",
            "goals": ["Q2 campaign launch", "Brand awareness", "Lead generation"],
            "progress": 68,
            "avatar": "👩‍🎨"
        },
        {
            "name": "Alex Thompson",
            "role": "Sales Manager",
            "department": "Sales",
            "goals": ["Enterprise Corp deal", "Revenue targets", "Customer acquisition"],
            "progress": 91,
            "avatar": "👨‍💼"
        }
    ]
    
    # Demo team metrics
    team_metrics = {
        "alignment_score": 87,
        "collaboration_index": 92,
        "goal_completion": 79,
        "communication_effectiveness": 85
    }
    
    context = {
        "request": request,
        "team": team,
        "metrics": team_metrics,
        "demo_mode": True
    }
    
    return templates.TemplateResponse("demo/team.html", context)


@router.get("/workflows", response_class=HTMLResponse)
async def demo_workflows(request: Request):
    """Workflow automation demo."""
    
    # Demo workflows
    workflows = [
        {
            "id": "workflow-123",
            "name": "Email Triage & Response",
            "type": "email_automation",
            "status": "active",
            "description": "Automatically categorizes emails and drafts responses",
            "metrics": {
                "emails_processed": 156,
                "time_saved": "8.5 hours",
                "accuracy": 94.2
            },
            "last_run": "2 minutes ago"
        },
        {
            "id": "workflow-456",
            "name": "Meeting Scheduling",
            "type": "calendar_automation",
            "status": "active",
            "description": "Schedules meetings based on availability and preferences",
            "metrics": {
                "meetings_scheduled": 23,
                "time_saved": "3.2 hours",
                "accuracy": 98.7
            },
            "last_run": "15 minutes ago"
        },
        {
            "id": "workflow-789",
            "name": "Task Creation & Assignment",
            "type": "project_automation",
            "status": "active",
            "description": "Creates tasks from conversations and assigns to team members",
            "metrics": {
                "tasks_created": 45,
                "time_saved": "2.1 hours",
                "accuracy": 91.5
            },
            "last_run": "1 hour ago"
        },
        {
            "id": "workflow-101",
            "name": "Performance Reporting",
            "type": "analytics_automation",
            "status": "active",
            "description": "Generates weekly performance reports and insights",
            "metrics": {
                "reports_generated": 12,
                "time_saved": "1.8 hours",
                "accuracy": 96.3
            },
            "last_run": "1 day ago"
        }
    ]
    
    # Demo automation stats
    automation_stats = {
        "total_workflows": 4,
        "active_workflows": 4,
        "total_time_saved": "15.6 hours",
        "total_automations": 236,
        "success_rate": 95.2
    }
    
    context = {
        "request": request,
        "workflows": workflows,
        "stats": automation_stats,
        "demo_mode": True
    }
    
    return templates.TemplateResponse("demo/workflows.html", context)


@router.get("/api/demo-data")
async def get_demo_data():
    """API endpoint for demo data."""
    
    demo_data = {
        "company": {
            "name": "TechFlow Solutions",
            "industry": "SaaS",
            "size": "50 employees",
            "description": "AI-powered workflow automation platform"
        },
        "users": [
            {
                "id": "U123456",
                "name": "Sarah Chen",
                "role": "CEO",
                "email": "sarah@techflow.com"
            },
            {
                "id": "U789012",
                "name": "Mike Rodriguez",
                "role": "CTO",
                "email": "mike@techflow.com"
            },
            {
                "id": "U345678",
                "name": "Jennifer Park",
                "role": "Marketing Director",
                "email": "jen@techflow.com"
            },
            {
                "id": "U901234",
                "name": "Alex Thompson",
                "role": "Sales Manager",
                "email": "alex@techflow.com"
            }
        ],
        "metrics": {
            "conversations": 12,
            "workflows": 8,
            "time_saved_hours": 15,
            "accuracy_percentage": 94.2
        }
    }
    
    return demo_data


@router.post("/api/demo-conversation")
async def create_demo_conversation(request: Request):
    """Create a demo conversation."""
    
    body = await request.json()
    message = body.get("message", "")
    
    # Demo response based on message content
    if "performance" in message.lower() or "goals" in message.lower():
        response = "Based on your data, you're at 87% of Q4 targets. Sales team is ahead by 12%, but marketing is 8% behind. Would you like me to create an action plan?"
    elif "meeting" in message.lower() or "schedule" in message.lower():
        response = "I've scheduled a meeting with the team for tomorrow at 2 PM. I've sent calendar invites and created an agenda focusing on Q2 planning."
    elif "task" in message.lower() or "create" in message.lower():
        response = "I've created a task for the team to review the budget. It's assigned with a due date of Friday and I'll send notifications."
    else:
        response = "I understand you're asking about " + message + ". Let me gather the relevant information and provide you with actionable insights."
    
    return {
        "conversation_id": str(uuid.uuid4()),
        "response": response,
        "timestamp": "2024-01-15T10:30:00Z",
        "demo_mode": True
    }


@router.get("/start-trial")
async def start_trial():
    """Redirect to trial signup."""
    return RedirectResponse(url="https://reflex.ai/signup?demo=true")


@router.get("/schedule-demo")
async def schedule_demo():
    """Redirect to demo scheduling."""
    return RedirectResponse(url="https://reflex.ai/demo?demo=true") 