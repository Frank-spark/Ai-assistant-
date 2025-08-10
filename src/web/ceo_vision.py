"""Enhanced CEO Vision web routes for comprehensive organizational template."""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
import base64

from src.auth.dependencies import get_current_user
from src.storage.db import get_db_session
from src.saas.models import User
from src.ai.ceo_vision_chain import get_ceo_vision_chain, CEOVisionContext
from src.analytics.telemetry import get_telemetry_service, EventType

router = APIRouter(prefix="/ceo", tags=["ceo-vision"])
templates = Jinja2Templates(directory="src/web/templates")


@router.get("/vision", response_class=HTMLResponse)
async def ceo_vision_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Enhanced CEO Vision Dashboard main page."""
    
    # Get CEO vision chain
    ceo_chain = get_ceo_vision_chain()
    
    # Get user's vision context (or create default)
    vision_context = await _get_user_vision_context(current_user, db)
    
    # Prepare comprehensive dashboard data
    dashboard_data = await _prepare_comprehensive_dashboard_data(vision_context, current_user)
    
    context = {
        "request": request,
        "user": current_user,
        **dashboard_data
    }
    
    return templates.TemplateResponse("dashboard/ceo_vision.html", context)


@router.post("/conversation")
async def ceo_conversation(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Process comprehensive CEO conversation."""
    try:
        body = await request.json()
        message = body.get("message", "")
        voice_output = body.get("voice_output", False)
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        # Get user's vision context
        vision_context = await _get_user_vision_context(current_user, db)
        
        # Process conversation
        result = await ceo_chain.ceo_conversation(
            context=vision_context,
            message=message,
            voice_input=False,
            voice_output=voice_output
        )
        
        # Track conversation
        telemetry = get_telemetry_service()
        await telemetry.track_event(
            EventType.AI_CONVERSATION_END,
            user_id=current_user.email,
            metadata={
                "conversation_type": "comprehensive_ceo_vision",
                "voice_output": voice_output,
                "message_length": len(message),
                "template_sections_used": result.get("template_sections_referenced", [])
            }
        )
        
        return {
            "success": True,
            "response": result["content"],
            "voice_data": result.get("voice_data"),
            "suggested_actions": result.get("suggested_actions", []),
            "template_sections": result.get("template_sections_referenced", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice")
async def process_voice_input(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Process voice input for comprehensive CEO conversation."""
    try:
        body = await request.json()
        audio_data = body.get("audio_data", "")
        voice_output = body.get("voice_output", False)
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="Audio data is required")
        
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_data)
        
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        # Get user's vision context
        vision_context = await _get_user_vision_context(current_user, db)
        
        # Process voice input
        transcription = await ceo_chain.process_voice_input(audio_bytes)
        
        # Process conversation
        result = await ceo_chain.ceo_conversation(
            context=vision_context,
            message=transcription,
            voice_input=True,
            voice_output=voice_output
        )
        
        # Track voice interaction
        telemetry = get_telemetry_service()
        await telemetry.track_event(
            EventType.FEATURE_USED,
            user_id=current_user.email,
            metadata={
                "feature": "comprehensive_ceo_voice_conversation",
                "voice_output": voice_output,
                "transcription_length": len(transcription),
                "template_sections_used": result.get("template_sections_referenced", [])
            }
        )
        
        return {
            "success": True,
            "transcription": transcription,
            "response": result["content"],
            "voice_data": result.get("voice_data"),
            "suggested_actions": result.get("suggested_actions", []),
            "template_sections": result.get("template_sections_referenced", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/summary")
async def get_vision_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get comprehensive CEO vision summary."""
    try:
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        # Get user's vision context
        vision_context = await _get_user_vision_context(current_user, db)
        
        # Get comprehensive summary
        summary = await ceo_chain.get_comprehensive_vision_summary(vision_context)
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision/update")
async def update_vision_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update comprehensive CEO vision data."""
    try:
        body = await request.json()
        updates = body.get("updates", {})
        
        if not updates:
            raise HTTPException(status_code=400, detail="Updates are required")
        
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        # Get user's vision context
        vision_context = await _get_user_vision_context(current_user, db)
        
        # Update comprehensive vision data
        success = await ceo_chain.update_comprehensive_vision_data(vision_context, updates)
        
        if success:
            return {
                "success": True,
                "message": "Comprehensive vision data updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update vision data")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision/initialize")
async def initialize_vision(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Initialize comprehensive CEO vision for a new company."""
    try:
        body = await request.json()
        company_name = body.get("company_name", "")
        ceo_name = body.get("ceo_name", current_user.first_name + " " + current_user.last_name)
        industry = body.get("industry", "")
        vision_data = body.get("vision_data", {})
        
        if not company_name:
            raise HTTPException(status_code=400, detail="Company name is required")
        
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        # Initialize comprehensive vision
        vision_context = await ceo_chain.initialize_ceo_vision(
            company_name=company_name,
            ceo_name=ceo_name,
            industry=industry,
            vision_data=vision_data
        )
        
        # Store in user profile
        current_user.company_name = company_name
        current_user.role = "CEO"
        db.commit()
        
        return {
            "success": True,
            "message": "Comprehensive CEO vision initialized successfully",
            "vision_context": {
                "company_name": vision_context.company_name,
                "ceo_name": vision_context.ceo_name,
                "industry": vision_context.industry,
                "template_sections": len(vision_context.vision_data.keys())
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/template")
async def get_vision_template(
    current_user: User = Depends(get_current_user)
):
    """Get the comprehensive vision template structure."""
    try:
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        return {
            "success": True,
            "template": ceo_chain.vision_template,
            "sections": [
                "leadership_roles",
                "organizational_structure", 
                "decision_escalation_paths",
                "core_processes_workflows",
                "performance_metrics_kpis",
                "strategic_goals_vision",
                "values_operating_principles",
                "products_services_technology",
                "risk_compliance_restrictions",
                "ai_roles_functions",
                "review_update_cycle"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision/section/{section_name}")
async def update_vision_section(
    section_name: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update a specific section of the CEO vision."""
    try:
        body = await request.json()
        section_data = body.get("data", {})
        
        if not section_data:
            raise HTTPException(status_code=400, detail="Section data is required")
        
        # Get CEO vision chain
        ceo_chain = get_ceo_vision_chain()
        
        # Get user's vision context
        vision_context = await _get_user_vision_context(current_user, db)
        
        # Update specific section
        updates = {section_name: section_data}
        success = await ceo_chain.update_comprehensive_vision_data(vision_context, updates)
        
        if success:
            return {
                "success": True,
                "message": f"Section '{section_name}' updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update section '{section_name}'")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_user_vision_context(user: User, db: Session) -> CEOVisionContext:
    """Get or create user's comprehensive vision context."""
    try:
        # Create comprehensive default context based on the 11-section template
        default_vision_data = {
            "leadership_roles": {
                "executive_team": [
                    {
                        "role": "CEO",
                        "name": f"{user.first_name} {user.last_name}",
                        "responsibilities": "Overall company strategy and leadership",
                        "decision_authority": "Final decision maker",
                        "reporting_to": "Board of Directors"
                    }
                ],
                "key_roles": {
                    "vp_engineering": {
                        "name": "To be hired",
                        "scope": "Technical leadership and product development",
                        "reporting": "Reports to CEO"
                    },
                    "vp_operations": {
                        "name": "To be hired", 
                        "scope": "Operations and execution",
                        "reporting": "Reports to CEO"
                    },
                    "cfo": {
                        "name": "To be hired",
                        "role": "Financial leadership",
                        "reporting": "Reports to CEO"
                    }
                },
                "decision_authority": {
                    "strategic_decisions": "CEO",
                    "operational_decisions": "VP Operations",
                    "technical_decisions": "VP Engineering",
                    "financial_decisions": "CFO"
                },
                "reporting_relationships": {
                    "vp_engineering": "CEO",
                    "vp_operations": "CEO", 
                    "cfo": "CEO"
                }
            },
            "organizational_structure": {
                "departments": [
                    {
                        "name": "Engineering",
                        "lead": "VP Engineering",
                        "purpose": "Product development and technical innovation",
                        "team_members": ["Software Engineers", "DevOps", "QA"],
                        "special_capabilities": ["AI/ML", "Cloud Infrastructure"]
                    },
                    {
                        "name": "Operations",
                        "lead": "VP Operations", 
                        "purpose": "Business operations and execution",
                        "team_members": ["Project Managers", "Operations Specialists"],
                        "special_capabilities": ["Process Optimization", "Automation"]
                    }
                ],
                "business_units": [],
                "geographic_regions": [],
                "functional_areas": ["Engineering", "Operations", "Finance", "Sales"],
                "team_hierarchy": {
                    "ceo": ["vp_engineering", "vp_operations", "cfo"],
                    "vp_engineering": ["engineering_team"],
                    "vp_operations": ["operations_team"]
                }
            },
            "decision_escalation_paths": {
                "decision_types": {
                    "technical_issues": ["VP Engineering", "CEO"],
                    "operational_issues": ["VP Operations", "CEO"],
                    "financial_issues": ["CFO", "CEO"],
                    "client_escalations": ["Supervisor", "VP Operations", "CEO"],
                    "strategic_decisions": ["CEO", "Board"]
                },
                "escalation_flows": {
                    "standard_escalation": ["Immediate Supervisor", "Department Head", "VP", "CEO"],
                    "urgent_escalation": ["Department Head", "CEO"],
                    "emergency_escalation": ["CEO", "Board"]
                },
                "approval_matrices": {
                    "budget_approval": {
                        "up_to_1k": "Supervisor",
                        "up_to_10k": "VP",
                        "up_to_100k": "CFO",
                        "above_100k": "CEO"
                    },
                    "hiring_approval": {
                        "junior_positions": "Department Head",
                        "senior_positions": "VP",
                        "executive_positions": "CEO"
                    }
                },
                "emergency_procedures": {
                    "security_incident": ["IT Security", "VP Engineering", "CEO"],
                    "financial_emergency": ["CFO", "CEO", "Board"],
                    "operational_crisis": ["VP Operations", "CEO"]
                }
            },
            "core_processes_workflows": {
                "operational_processes": [
                    {
                        "name": "Product Development",
                        "steps": ["Requirements", "Design", "Development", "Testing", "Deployment"],
                        "handoffs": ["Product Manager", "Designer", "Developer", "QA", "DevOps"],
                        "approvals": ["VP Engineering", "CEO"]
                    },
                    {
                        "name": "Customer Onboarding",
                        "steps": ["Lead Qualification", "Proposal", "Contract", "Implementation"],
                        "handoffs": ["Sales", "Account Manager", "Implementation Team"],
                        "approvals": ["VP Operations", "CEO"]
                    }
                ],
                "approval_workflows": {
                    "expense_approval": ["Employee", "Manager", "Finance"],
                    "contract_approval": ["Legal", "VP", "CEO"],
                    "policy_approval": ["HR", "Legal", "CEO"]
                },
                "handoff_procedures": {
                    "project_handoff": ["Documentation", "Knowledge Transfer", "Sign-off"],
                    "employee_handoff": ["Exit Interview", "Knowledge Transfer", "Access Removal"]
                },
                "documentation_requirements": {
                    "project_docs": ["Requirements", "Design", "API Docs", "User Manuals"],
                    "process_docs": ["SOPs", "Work Instructions", "Training Materials"],
                    "compliance_docs": ["Policies", "Procedures", "Audit Reports"]
                },
                "quality_controls": {
                    "code_review": "Mandatory for all changes",
                    "testing": "Unit, Integration, E2E",
                    "deployment": "Staging, Production approval"
                }
            },
            "performance_metrics_kpis": {
                "business_metrics": {
                    "revenue_growth": {"target": "25%", "measurement": "Quarterly"},
                    "customer_satisfaction": {"target": "90%", "measurement": "Monthly"},
                    "market_share": {"target": "15%", "measurement": "Annually"}
                },
                "operational_metrics": {
                    "project_delivery_time": {"target": "On schedule", "measurement": "Per project"},
                    "system_uptime": {"target": "99.9%", "measurement": "Monthly"},
                    "bug_resolution_time": {"target": "24 hours", "measurement": "Per incident"}
                },
                "financial_metrics": {
                    "profit_margin": {"target": "30%", "measurement": "Monthly"},
                    "cash_flow": {"target": "Positive", "measurement": "Monthly"},
                    "burn_rate": {"target": "Sustainable", "measurement": "Monthly"}
                },
                "team_metrics": {
                    "employee_satisfaction": {"target": "85%", "measurement": "Quarterly"},
                    "retention_rate": {"target": "90%", "measurement": "Annually"},
                    "productivity": {"target": "Increasing", "measurement": "Monthly"}
                },
                "customer_metrics": {
                    "net_promoter_score": {"target": "50+", "measurement": "Quarterly"},
                    "customer_lifetime_value": {"target": "Increasing", "measurement": "Monthly"},
                    "churn_rate": {"target": "<5%", "measurement": "Monthly"}
                },
                "tracking_frequency": {
                    "daily": ["System uptime", "Active users"],
                    "weekly": ["Project progress", "Team velocity"],
                    "monthly": ["Financial metrics", "Customer metrics"],
                    "quarterly": ["Strategic goals", "Employee satisfaction"]
                }
            },
            "strategic_goals_vision": {
                "short_term_goals": {
                    "q1": "Launch MVP and acquire first 100 customers",
                    "q2": "Achieve $1M ARR and expand team to 20 people",
                    "q3": "Enter new market segment and reach $2M ARR",
                    "q4": "Prepare for Series A funding round"
                },
                "medium_term_goals": {
                    "year_1": "Establish market presence and achieve $5M ARR",
                    "year_2": "Scale operations and expand to international markets",
                    "year_3": "Achieve market leadership position with $20M ARR"
                },
                "long_term_goals": {
                    "year_5": "Become industry leader with $100M ARR",
                    "year_10": "Global expansion and potential IPO"
                },
                "strategic_themes": [
                    "AI-powered productivity",
                    "User-friendly design", 
                    "Comprehensive integration",
                    "Global scalability"
                ],
                "vision_statement": "To become the leading AI assistant platform that makes powerful AI capabilities accessible to businesses of all sizes worldwide.",
                "mission_statement": "Empowering businesses with intelligent automation and AI-driven insights to achieve their full potential.",
                "competitive_positioning": "The most user-friendly, comprehensive, and affordable AI assistant platform for businesses."
            },
            "values_operating_principles": {
                "core_values": [
                    "Innovation and excellence in everything we do",
                    "Customer focus and satisfaction",
                    "Team collaboration and mutual respect",
                    "Continuous learning and improvement",
                    "Integrity and transparency"
                ],
                "operating_principles": [
                    "Data-driven decision making",
                    "Agile methodology and rapid iteration",
                    "Transparent communication at all levels",
                    "Empowerment and accountability",
                    "Sustainable growth and profitability"
                ],
                "cultural_expectations": [
                    "Proactive problem solving",
                    "Continuous skill development",
                    "Cross-functional collaboration",
                    "Customer-centric thinking",
                    "Results-oriented approach"
                ],
                "decision_frameworks": [
                    "Impact vs. effort analysis",
                    "Risk vs. reward evaluation",
                    "Customer value assessment",
                    "Long-term sustainability consideration"
                ],
                "ethical_guidelines": [
                    "Honest and transparent communication",
                    "Respect for customer privacy and data",
                    "Fair treatment of employees and partners",
                    "Compliance with all applicable laws and regulations"
                ]
            },
            "products_services_technology": {
                "products": [
                    {
                        "name": "Reflex AI Assistant",
                        "description": "AI-powered executive assistant platform",
                        "target_market": "Businesses of all sizes",
                        "key_features": ["Voice conversations", "Multi-platform integration", "Advanced analytics"]
                    }
                ],
                "services": [
                    {
                        "name": "Implementation Support",
                        "description": "Professional services for platform setup and integration",
                        "target_market": "Enterprise customers"
                    },
                    {
                        "name": "Training and Consulting",
                        "description": "AI adoption and best practices consulting",
                        "target_market": "All customers"
                    }
                ],
                "key_technologies": [
                    "Artificial Intelligence and Machine Learning",
                    "Natural Language Processing",
                    "Cloud Computing and Microservices",
                    "Real-time Communication APIs",
                    "Advanced Analytics and Business Intelligence"
                ],
                "innovation_priorities": [
                    "Advanced AI capabilities",
                    "Seamless integration ecosystem",
                    "Real-time voice processing",
                    "Predictive analytics",
                    "Automated workflow optimization"
                ],
                "technology_stack": {
                    "frontend": ["React", "TypeScript", "Tailwind CSS"],
                    "backend": ["Python", "FastAPI", "PostgreSQL"],
                    "ai_ml": ["OpenAI", "Anthropic", "LangChain"],
                    "infrastructure": ["AWS", "Docker", "Kubernetes"]
                },
                "development_methodologies": [
                    "Agile/Scrum",
                    "Continuous Integration/Deployment",
                    "Test-Driven Development",
                    "DevOps practices"
                ]
            },
            "risk_compliance_restrictions": {
                "compliance_standards": [
                    "GDPR (Data Protection)",
                    "SOC 2 (Security)",
                    "ISO 27001 (Information Security)",
                    "PCI DSS (Payment Security)"
                ],
                "regulatory_requirements": [
                    "Data privacy regulations",
                    "Financial reporting requirements",
                    "Employment law compliance",
                    "Industry-specific regulations"
                ],
                "market_restrictions": [
                    "Geographic limitations",
                    "Industry restrictions",
                    "Export controls"
                ],
                "activity_restrictions": [
                    "No illegal activities",
                    "No unethical AI usage",
                    "No unauthorized data access",
                    "No discriminatory practices"
                ],
                "known_risks": {
                    "cybersecurity": {
                        "risk": "Data breaches and security incidents",
                        "mitigation": "Regular security audits, encryption, access controls"
                    },
                    "regulatory": {
                        "risk": "Changing compliance requirements",
                        "mitigation": "Regular compliance reviews, legal consultation"
                    },
                    "market": {
                        "risk": "Competitive pressure and market changes",
                        "mitigation": "Continuous innovation, market monitoring"
                    }
                },
                "mitigation_plans": {
                    "security_incident": ["Immediate containment", "Investigation", "Communication", "Recovery"],
                    "compliance_violation": ["Assessment", "Remediation", "Reporting", "Prevention"],
                    "market_disruption": ["Analysis", "Strategy adjustment", "Communication", "Execution"]
                },
                "risk_tolerance_levels": {
                    "low": "Compliance and security risks",
                    "medium": "Operational and market risks", 
                    "high": "Innovation and growth risks"
                }
            },
            "ai_roles_functions": {
                "ai_personas": [
                    {
                        "name": "Executive Assistant",
                        "purpose": "Strategic support and decision assistance",
                        "capabilities": ["Strategic analysis", "Meeting preparation", "Communication drafting"]
                    },
                    {
                        "name": "Operations Manager",
                        "purpose": "Process optimization and workflow management",
                        "capabilities": ["Process analysis", "Automation recommendations", "Performance monitoring"]
                    },
                    {
                        "name": "Data Analyst",
                        "purpose": "Insights and analytics support",
                        "capabilities": ["Data analysis", "Trend identification", "Report generation"]
                    }
                ],
                "ai_functions": {
                    "strategic_planning": "Assist with strategic decision making and planning",
                    "performance_monitoring": "Track KPIs and provide insights",
                    "communication_support": "Draft communications and presentations",
                    "process_optimization": "Identify and implement process improvements",
                    "risk_assessment": "Monitor and assess business risks"
                },
                "ai_limitations": [
                    "Cannot make final strategic decisions",
                    "Cannot access confidential information without authorization",
                    "Cannot replace human judgment in complex situations",
                    "Must comply with all company policies and ethical guidelines"
                ],
                "ai_guidelines": {
                    "transparency": "Always disclose AI involvement in communications",
                    "accuracy": "Verify information before providing recommendations",
                    "privacy": "Respect all privacy and confidentiality requirements",
                    "ethics": "Follow ethical AI principles and company values"
                },
                "ai_decision_authority": {
                    "recommendations": "Provide data-driven recommendations",
                    "analysis": "Conduct comprehensive analysis",
                    "monitoring": "Monitor performance and trends",
                    "automation": "Automate routine tasks and processes"
                }
            },
            "review_update_cycle": {
                "review_frequency": "Quarterly comprehensive review",
                "update_triggers": [
                    "Leadership changes",
                    "Major strategic pivots",
                    "Department restructuring",
                    "Significant market changes",
                    "Regulatory updates"
                ],
                "version_control": {
                    "document_versioning": "Track all changes with version numbers",
                    "approval_process": "CEO approval required for major changes",
                    "change_documentation": "Document all changes and rationale"
                },
                "stakeholder_approval": {
                    "executive_team": "Review and approve strategic changes",
                    "board_of_directors": "Approve major strategic pivots",
                    "legal_compliance": "Review compliance-related changes"
                },
                "change_management": {
                    "communication_plan": "Communicate changes to all stakeholders",
                    "training_requirements": "Provide training for new processes",
                    "implementation_timeline": "Gradual rollout of major changes"
                }
            }
        }
        
        return CEOVisionContext(
            company_name=user.company_name or "Your Company",
            ceo_name=f"{user.first_name} {user.last_name}",
            industry=user.role or "Technology",
            vision_data=default_vision_data
        )
        
    except Exception as e:
        # Return minimal context if there's an error
        return CEOVisionContext(
            company_name="Your Company",
            ceo_name=f"{user.first_name} {user.last_name}",
            industry="Technology",
            vision_data={}
        )


async def _prepare_comprehensive_dashboard_data(vision_context: CEOVisionContext, user: User) -> Dict[str, Any]:
    """Prepare comprehensive data for the CEO vision dashboard."""
    try:
        # Extract data from comprehensive vision context
        vision_data = vision_context.vision_data
        
        # Leadership structure
        leadership = {}
        if "leadership_roles" in vision_data:
            key_roles = vision_data["leadership_roles"].get("key_roles", {})
            for role, details in key_roles.items():
                leadership[role] = {
                    "name": details.get("name", "Open"),
                    "responsibilities": details.get("scope", ""),
                    "reports_to": details.get("reporting", "CEO")
                }
        
        # Strategic goals
        strategic_goals = []
        if "strategic_goals_vision" in vision_data:
            short_term = vision_data["strategic_goals_vision"].get("short_term_goals", {})
            for period, goal in short_term.items():
                strategic_goals.append({
                    "title": f"{period.upper()} Goal",
                    "description": goal,
                    "status": "on-track",
                    "progress": 25  # Placeholder
                })
        
        # KPIs
        kpis = {}
        if "performance_metrics_kpis" in vision_data:
            metrics = vision_data["performance_metrics_kpis"]
            kpis = {
                "revenue_target": "$1M",
                "team_size": "10",
                "projects_active": "5",
                "satisfaction_score": "85"
            }
        
        # Core values
        core_values = []
        if "values_operating_principles" in vision_data:
            values = vision_data["values_operating_principles"].get("core_values", [])
            for value in values:
                core_values.append({
                    "title": value,
                    "description": f"Core value: {value}"
                })
        
        # Operating principles
        operating_principles = []
        if "values_operating_principles" in vision_data:
            principles = vision_data["values_operating_principles"].get("operating_principles", [])
            for principle in principles:
                operating_principles.append({
                    "title": principle,
                    "description": f"Operating principle: {principle}"
                })
        
        # Escalation paths
        escalation_paths = []
        if "decision_escalation_paths" in vision_data:
            decision_types = vision_data["decision_escalation_paths"].get("decision_types", {})
            for issue_type, escalation_chain in decision_types.items():
                escalation_paths.append({
                    "trigger": issue_type.replace("_", " ").title(),
                    "escalation_chain": escalation_chain
                })
        
        # Decision matrices
        decision_matrices = []
        if "decision_escalation_paths" in vision_data:
            approval_matrices = vision_data["decision_escalation_paths"].get("approval_matrices", {})
            for matrix_type, matrix_data in approval_matrices.items():
                for threshold, authority in matrix_data.items():
                    decision_matrices.append({
                        "type": matrix_type.replace("_", " ").title(),
                        "authority": authority,
                        "threshold": threshold.replace("_", " ").title()
                    })
        
        # Template completion status
        template_completion = {}
        for section_name, section_data in vision_data.items():
            if isinstance(section_data, dict):
                completion = len([k for k, v in section_data.items() if v]) / len(section_data) * 100
            elif isinstance(section_data, list):
                completion = 100 if section_data else 0
            else:
                completion = 100 if section_data else 0
            
            template_completion[section_name] = completion
        
        return {
            "company_name": vision_context.company_name,
            "ceo_name": vision_context.ceo_name,
            "industry": vision_context.industry,
            "current_year": vision_context.current_year,
            "leadership": leadership,
            "strategic_goals": strategic_goals,
            "kpis": kpis,
            "core_values": core_values,
            "operating_principles": operating_principles,
            "escalation_paths": escalation_paths,
            "decision_matrices": decision_matrices,
            "leadership_structure": leadership,
            "short_term_goals": strategic_goals,
            "long_term_vision": vision_data.get("strategic_goals_vision", {}).get("vision_statement", "Vision to be defined"),
            "template_completion": template_completion,
            "vision_data": vision_data
        }
        
    except Exception as e:
        # Return minimal data if there's an error
        return {
            "company_name": "Your Company",
            "ceo_name": f"{user.first_name} {user.last_name}",
            "industry": "Technology",
            "current_year": 2024,
            "leadership": {},
            "strategic_goals": [],
            "kpis": {},
            "core_values": [],
            "operating_principles": [],
            "escalation_paths": [],
            "decision_matrices": [],
            "leadership_structure": {},
            "short_term_goals": [],
            "long_term_vision": "Vision to be defined",
            "template_completion": {},
            "vision_data": {}
        } 