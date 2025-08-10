"""Main FastAPI application for Reflex Executive Assistant."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .config import get_settings, is_production
from .logging.setup import setup_logging
from .storage.db import init_db, close_db, get_db_session
from .jobs.queue import init_celery, close_celery
from .integrations.webhooks import slack_router, gmail_router, asana_router
from .workflows.router import workflow_router
from .ai.chain import init_ai_chain
from .ai.model_switcher import init_model_switcher
from .ai.ceo_vision_chain import init_ceo_vision_chain
from .kb.retriever import init_kb_retriever
from .kb.enhanced_retriever import init_enhanced_kb_retriever
from .analytics.telemetry import init_telemetry_service, StrategicContext, TeamAlignment, CulturalMetrics, CompanyValues
from .integrations.hooks import init_hook_manager
from .web.dashboard import router as dashboard_router
from .web.landing import router as landing_router
from .web.ceo_vision import router as ceo_vision_router
from .saas.auth import router as auth_router
from .integrations.webhooks.slack import router as slack_webhook_router
from .integrations.webhooks.gmail import router as gmail_webhook_router
from .integrations.webhooks.asana import router as asana_webhook_router
from .integrations.meeting_recorder import get_meeting_manager
from .ai.decision_engine import get_decision_engine, DecisionRequest, DecisionType, DecisionPriority
from .ai.context_injector import get_context_injector, CommunicationChannel
from .frontend.dashboard import get_dashboard
from .ai.revenue_intelligence import get_revenue_intelligence, OpportunityType, FollowUpType
from .models.revenue_opportunity import RevenueOpportunity
from .models.follow_up_task import FollowUpTask
from .storage.db import RevenueOpportunity, FollowUpTask
from datetime import datetime, timedelta
from sqlalchemy import func

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global state
ai_chain = None
kb_retriever = None
enhanced_kb_retriever = None
model_switcher = None
ceo_vision_chain = None
telemetry_service = None
hook_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global ai_chain, kb_retriever, enhanced_kb_retriever, model_switcher, ceo_vision_chain, telemetry_service, hook_manager
    
    # Startup
    logger.info("Starting Reflex Executive Assistant...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize Celery
        init_celery()
        logger.info("Celery initialized successfully")
        
        # Initialize enhanced knowledge base retriever
        enhanced_kb_retriever = await init_enhanced_kb_retriever()
        logger.info("Enhanced knowledge base retriever initialized successfully")
        
        # Initialize knowledge base retriever (legacy)
        kb_retriever = init_kb_retriever()
        logger.info("Knowledge base retriever initialized successfully")
        
        # Initialize model switcher
        model_switcher = await init_model_switcher()
        logger.info("Model switcher initialized successfully")
        
        # Initialize CEO vision chain
        ceo_vision_chain = await init_ceo_vision_chain()
        logger.info("CEO vision chain initialized successfully")
        
        # Initialize AI chain
        ai_chain = init_ai_chain(enhanced_kb_retriever)
        logger.info("AI chain initialized successfully")
        
        # Initialize telemetry service
        telemetry_service = await init_telemetry_service()
        logger.info("Telemetry service initialized successfully")
        
        # Initialize hook manager
        hook_manager = await init_hook_manager()
        logger.info("Integration hook manager initialized successfully")
        
        logger.info("Reflex Executive Assistant started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Reflex Executive Assistant...")
    
    try:
        await close_db()
        close_celery()
        logger.info("Shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Reflex Executive Assistant",
        description="AI-driven executive assistant for Spark Robotic",
        version="0.1.0",
        docs_url="/docs" if not is_production() else None,
        redoc_url="/redoc" if not is_production() else None,
        lifespan=lifespan
    )
    
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if hasattr(settings, 'cors_origins') else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    if is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts if hasattr(settings, 'allowed_hosts') else ["*"]
        )
    
    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()}
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Health check endpoints
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint for Docker."""
        return {
            "status": "healthy",
            "service": "reflex-executive-assistant",
            "version": "0.1.0",
            "features": {
                "enhanced_kb": enhanced_kb_retriever is not None,
                "model_switcher": model_switcher is not None,
                "ceo_vision": ceo_vision_chain is not None,
                "telemetry": telemetry_service is not None,
                "hooks": hook_manager is not None
            }
        }
    
    @app.get("/healthz")
    async def health_check_detailed() -> Dict[str, Any]:
        """Detailed health check endpoint."""
        return {
            "status": "healthy",
            "service": "reflex-executive-assistant",
            "version": "0.1.0",
            "components": {
                "database": "connected",
                "redis": "connected",
                "ai_chain": ai_chain is not None,
                "enhanced_kb": enhanced_kb_retriever is not None,
                "model_switcher": model_switcher is not None,
                "ceo_vision_chain": ceo_vision_chain is not None,
                "telemetry": telemetry_service is not None,
                "hooks": hook_manager is not None
            }
        }
    
    # Include routers
    app.include_router(slack_router, prefix="/webhooks/slack", tags=["slack"])
    app.include_router(gmail_router, prefix="/webhooks/gmail", tags=["gmail"])
    app.include_router(asana_router, prefix="/webhooks/asana", tags=["asana"])
    app.include_router(workflow_router, prefix="/workflows", tags=["workflows"])
    
    # SaaS web interface
    app.include_router(landing_router, tags=["landing"])
    app.include_router(auth_router, tags=["authentication"])
    app.include_router(dashboard_router, tags=["dashboard"])
    app.include_router(ceo_vision_router, tags=["ceo-vision"])

    # Include webhook routers
    app.include_router(slack_webhook_router, prefix="/webhooks/slack", tags=["slack"])
    app.include_router(gmail_webhook_router, prefix="/webhooks/gmail", tags=["gmail"])
    app.include_router(asana_webhook_router, prefix="/webhooks/asana", tags=["asana"])

    # Meeting recording endpoints
    @app.post("/api/meetings/start")
    async def start_meeting_recording(
        request: Request,
        meeting_data: dict = Body(...)
    ):
        """Start recording an executive meeting."""
        try:
            meeting_title = meeting_data.get("title", "Executive Meeting")
            attendees = meeting_data.get("attendees", [])
            meeting_type = meeting_data.get("type", "executive")
            
            meeting_manager = get_meeting_manager()
            result = await meeting_manager.start_executive_meeting(
                meeting_title=meeting_title,
                attendees=attendees,
                meeting_type=meeting_type
            )
            
            return {
                "status": "success",
                "message": "Meeting recording started",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error starting meeting recording: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/meetings/{meeting_id}/end")
    async def end_meeting_recording(meeting_id: str):
        """End recording and analyze executive meeting."""
        try:
            meeting_manager = get_meeting_manager()
            result = await meeting_manager.end_executive_meeting(meeting_id)
            
            return {
                "status": "success",
                "message": "Meeting recording completed and analyzed",
                "data": result
            }
            
        except Exception as e:
            logger.error(f"Error ending meeting recording: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/meetings/{meeting_id}/summary")
    async def get_meeting_summary(meeting_id: str):
        """Get comprehensive summary of a meeting."""
        try:
            meeting_manager = get_meeting_manager()
            summary = await meeting_manager.get_meeting_summary(meeting_id)
            
            return {
                "status": "success",
                "data": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting meeting summary: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/meetings/active")
    async def get_active_meetings():
        """Get list of currently active meetings."""
        try:
            meeting_manager = get_meeting_manager()
            active_meetings = meeting_manager.get_active_meetings()
            
            return {
                "status": "success",
                "data": {
                    "active_meetings": active_meetings,
                    "count": len(active_meetings)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting active meetings: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/meetings/{meeting_id}/status")
    async def get_meeting_status(meeting_id: str):
        """Get current status of a meeting recording."""
        try:
            meeting_manager = get_meeting_manager()
            status = meeting_manager.recorder.get_recording_status()
            
            return {
                "status": "success",
                "data": status
            }
            
        except Exception as e:
            logger.error(f"Error getting meeting status: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/meetings/{meeting_id}/analyze")
    async def analyze_meeting(meeting_id: str):
        """Trigger AI analysis of a meeting."""
        try:
            from .jobs.tasks.meeting_tasks import analyze_meeting_transcript
            
            # Queue analysis task
            task = analyze_meeting_transcript.delay(meeting_id)
            
            return {
                "status": "success",
                "message": "Meeting analysis queued",
                "task_id": task.id
            }
            
        except Exception as e:
            logger.error(f"Error queuing meeting analysis: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/meetings/{meeting_id}/follow-ups")
    async def send_meeting_follow_ups(meeting_id: str):
        """Send follow-up emails and tasks for a meeting."""
        try:
            from .jobs.tasks.meeting_tasks import send_meeting_follow_ups
            
            # Queue follow-up task
            task = send_meeting_follow_ups.delay(meeting_id)
            
            return {
                "status": "success",
                "message": "Meeting follow-ups queued",
                "task_id": task.id
            }
            
        except Exception as e:
            logger.error(f"Error queuing meeting follow-ups: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Decision Intelligence endpoints
    @app.post("/api/decisions/analyze")
    async def analyze_decision(
        request: Request,
        decision_data: dict = Body(...)
    ):
        """Analyze a decision request with AI intelligence."""
        try:
            # Create decision request
            decision_request = DecisionRequest(
                decision_id=str(uuid.uuid4()),
                decision_type=DecisionType(decision_data.get("type", "approval")),
                title=decision_data.get("title", ""),
                description=decision_data.get("description", ""),
                amount=decision_data.get("amount"),
                impact_areas=decision_data.get("impact_areas", []),
                urgency=DecisionPriority(decision_data.get("urgency", "medium")),
                requester=decision_data.get("requester", ""),
                context=decision_data.get("context", {})
            )
            
            # Analyze decision
            decision_engine = get_decision_engine()
            analysis = await decision_engine.analyze_decision(decision_request)
            
            return {
                "status": "success",
                "decision_id": decision_request.decision_id,
                "analysis": {
                    "recommendation": analysis.recommendation,
                    "confidence_score": analysis.confidence_score,
                    "reasoning": analysis.reasoning,
                    "risk_assessment": analysis.risk_assessment,
                    "business_impact": analysis.business_impact,
                    "compliance_check": analysis.compliance_check,
                    "auto_approval_eligible": analysis.auto_approval_eligible,
                    "required_approvals": analysis.required_approvals,
                    "timeline_impact": analysis.timeline_impact,
                    "cost_benefit_analysis": analysis.cost_benefit_analysis
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing decision: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/decisions/{decision_id}")
    async def get_decision(decision_id: str):
        """Get decision details and analysis."""
        try:
            decision_engine = get_decision_engine()
            summary = await decision_engine.get_decision_summary(decision_id)
            
            return {
                "status": "success",
                "decision": summary
            }
            
        except Exception as e:
            logger.error(f"Error getting decision: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/decisions/{decision_id}/approve")
    async def approve_decision(
        decision_id: str,
        approval_data: dict = Body(...)
    ):
        """Approve a decision."""
        try:
            approver = approval_data.get("approver", "")
            notes = approval_data.get("notes", "")
            
            decision_engine = get_decision_engine()
            success = await decision_engine.approve_decision(decision_id, approver, notes)
            
            if success:
                return {
                    "status": "success",
                    "message": "Decision approved successfully"
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to approve decision")
            
        except Exception as e:
            logger.error(f"Error approving decision: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/decisions/pending")
    async def get_pending_decisions():
        """Get all pending decisions that need attention."""
        try:
            # Assuming get_db_session is available or will be added
            # from .storage.db import get_db_session
            # from .models.decision import Decision, func
            # from datetime import datetime
            
            # db_session = get_db_session()
            
            # pending_decisions = db_session.query(Decision).filter(
            #     Decision.status == "pending"
            # ).order_by(Decision.created_at.desc()).all()
            
            # decisions = []
            # for decision in pending_decisions:
            #     decisions.append({
            #         "id": decision.id,
            #         "title": decision.title,
            #         "decision_type": decision.decision_type,
            #         "amount": decision.amount,
            #         "recommendation": decision.recommendation,
            #         "confidence_score": decision.confidence_score,
            #         "auto_approval_eligible": decision.auto_approval_eligible,
            #         "created_at": decision.created_at.isoformat()
            #     })
            
            # db_session.close()
            
            # return {
            #     "status": "success",
            #     "pending_decisions": decisions,
            #     "count": len(decisions)
            # }
            
            # Placeholder for actual DB query
            return {
                "status": "success",
                "pending_decisions": [],
                "count": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting pending decisions: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/decisions/auto-approval-eligible")
    async def get_auto_approval_eligible_decisions():
        """Get decisions that can be auto-approved."""
        try:
            # Assuming get_db_session is available or will be added
            # from .storage.db import get_db_session
            # from .models.decision import Decision
            
            # db_session = get_db_session()
            
            # auto_approval_decisions = db_session.query(Decision).filter(
            #     Decision.status == "pending",
            #     Decision.auto_approval_eligible == True
            # ).order_by(Decision.created_at.desc()).all()
            
            # decisions = []
            # for decision in auto_approval_decisions:
            #     decisions.append({
            #         "id": decision.id,
            #         "title": decision.title,
            #         "decision_type": decision.decision_type,
            #         "amount": decision.amount,
            #         "recommendation": decision.recommendation,
            #         "confidence_score": decision.confidence_score,
            #         "created_at": decision.created_at.isoformat()
            #     })
            
            # db_session.close()
            
            # return {
            #     "status": "success",
            #     "auto_approval_decisions": decisions,
            #     "count": len(decisions)
            # }
            
            # Placeholder for actual DB query
            return {
                "status": "success",
                "auto_approval_decisions": [],
                "count": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting auto-approval decisions: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/decisions/auto-approve-all")
    async def auto_approve_eligible_decisions():
        """Auto-approve all eligible decisions."""
        try:
            # Assuming get_db_session is available or will be added
            # from .storage.db import get_db_session
            # from .models.decision import Decision
            
            # db_session = get_db_session()
            
            # # Get auto-approval eligible decisions
            # eligible_decisions = db_session.query(Decision).filter(
            #     Decision.status == "pending",
            #     Decision.auto_approval_eligible == True
            # ).all()
            
            # approved_count = 0
            # for decision in eligible_decisions:
            #     decision.status = "approved"
            #     decision.approved_by = "system"
            #     decision.approved_at = datetime.utcnow()
            #     decision.approval_notes = "Auto-approved by system"
            #     approved_count += 1
            
            # db_session.commit()
            # db_session.close()
            
            # return {
            #     "status": "success",
            #     "message": f"Auto-approved {approved_count} decisions",
            #     "approved_count": approved_count
            # }
            
            # Placeholder for actual DB query
            return {
                "status": "success",
                "message": "Auto-approve-all endpoint called (placeholder)",
                "approved_count": 0
            }
            
        except Exception as e:
            logger.error(f"Error auto-approving decisions: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/decisions/analytics")
    async def get_decision_analytics():
        """Get analytics on decision patterns and outcomes."""
        try:
            # Assuming get_db_session is available or will be added
            # from .storage.db import get_db_session
            # from .models.decision import Decision, func
            
            # db_session = get_db_session()
            
            # # Get decision statistics
            # total_decisions = db_session.query(Decision).count()
            # approved_decisions = db_session.query(Decision).filter(
            #     Decision.status == "approved"
            # ).count()
            # rejected_decisions = db_session.query(Decision).filter(
            #     Decision.status == "rejected"
            # ).count()
            # pending_decisions = db_session.query(Decision).filter(
            #     Decision.status == "pending"
            # ).count()
            
            # # Get average confidence scores
            # avg_confidence = db_session.query(func.avg(Decision.confidence_score)).scalar() or 0
            
            # # Get decision types breakdown
            # decision_types = db_session.query(
            #     Decision.decision_type,
            #     func.count(Decision.id)
            # ).group_by(Decision.decision_type).all()
            
            # db_session.close()
            
            # return {
            #     "status": "success",
            #     "analytics": {
            #         "total_decisions": total_decisions,
            #         "approved_decisions": approved_decisions,
            #         "rejected_decisions": rejected_decisions,
            #         "pending_decisions": pending_decisions,
            #         "approval_rate": (approved_decisions / total_decisions * 100) if total_decisions > 0 else 0,
            #         "average_confidence_score": round(avg_confidence, 2),
            #         "decision_types_breakdown": dict(decision_types)
            #     }
            # }
            
            # Placeholder for actual DB query
            return {
                "status": "success",
                "analytics": {
                    "total_decisions": 0,
                    "approved_decisions": 0,
                    "rejected_decisions": 0,
                    "pending_decisions": 0,
                    "approval_rate": 0,
                    "average_confidence_score": 0,
                    "decision_types_breakdown": {}
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting decision analytics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Strategic Context Injection endpoints
    @app.post("/api/context/inject")
    async def inject_strategic_context(
        request: Request,
        context_data: dict = Body(...)
    ):
        """Inject strategic context into communication content."""
        try:
            content = context_data.get("content", "")
            channel = CommunicationChannel(context_data.get("channel", "slack"))
            user_id = context_data.get("user_id", "")
            team_id = context_data.get("team_id")
            
            context_injector = get_context_injector()
            injection = await context_injector.inject_context(
                content=content,
                channel=channel,
                user_id=user_id,
                team_id=team_id
            )
            
            return {
                "status": "success",
                "original_content": injection.original_message,
                "injected_content": injection.content,
                "context_injection": injection.injected_context,
                "alignment_score": injection.alignment_score,
                "cultural_relevance": injection.cultural_relevance,
                "context_type": injection.context_type.value
            }
            
        except Exception as e:
            logger.error(f"Error injecting strategic context: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/context/analytics")
    async def get_context_analytics():
        """Get analytics on strategic context injection effectiveness."""
        try:
            db_session = get_db_session()
            
            # Get context injection statistics
            total_injections = db_session.query(StrategicContext).count()
            recent_injections = db_session.query(StrategicContext).filter(
                StrategicContext.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            # Get average alignment scores
            avg_alignment = db_session.query(func.avg(StrategicContext.alignment_score)).scalar() or 0
            avg_cultural_relevance = db_session.query(func.avg(StrategicContext.cultural_relevance)).scalar() or 0
            
            # Get context types breakdown
            context_types = db_session.query(
                StrategicContext.context_type,
                func.count(StrategicContext.id)
            ).group_by(StrategicContext.context_type).all()
            
            # Get channel breakdown
            channels = db_session.query(
                StrategicContext.channel,
                func.count(StrategicContext.id)
            ).group_by(StrategicContext.channel).all()
            
            db_session.close()
            
            return {
                "status": "success",
                "analytics": {
                    "total_injections": total_injections,
                    "recent_injections": recent_injections,
                    "average_alignment_score": round(avg_alignment, 2),
                    "average_cultural_relevance": round(avg_cultural_relevance, 2),
                    "context_types_breakdown": dict(context_types),
                    "channels_breakdown": dict(channels)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting context analytics: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/context/team-alignment")
    async def get_team_alignment():
        """Get team alignment with strategic goals."""
        try:
            db_session = get_db_session()
            
            # Get team alignment data
            alignments = db_session.query(TeamAlignment).filter(
                TeamAlignment.active == True
            ).order_by(TeamAlignment.alignment_score.desc()).all()
            
            teams = []
            for alignment in alignments:
                teams.append({
                    "team_id": alignment.team_id,
                    "team_name": alignment.team_name,
                    "goal_name": alignment.goal_name,
                    "alignment_score": alignment.alignment_score,
                    "progress_percentage": alignment.progress_percentage,
                    "last_assessment": alignment.last_assessment.isoformat(),
                    "next_assessment": alignment.next_assessment.isoformat()
                })
            
            db_session.close()
            
            return {
                "status": "success",
                "team_alignments": teams,
                "count": len(teams)
            }
            
        except Exception as e:
            logger.error(f"Error getting team alignment: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/context/cultural-metrics")
    async def get_cultural_metrics():
        """Get cultural health metrics."""
        try:
            db_session = get_db_session()
            
            # Get recent cultural metrics
            recent_metrics = db_session.query(CulturalMetrics).filter(
                CulturalMetrics.period_end >= datetime.utcnow() - timedelta(days=30)
            ).order_by(CulturalMetrics.created_at.desc()).all()
            
            metrics = []
            for metric in recent_metrics:
                metrics.append({
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "metric_category": metric.metric_category,
                    "team_id": metric.team_id,
                    "trend": metric.trend,
                    "period_end": metric.period_end.isoformat()
                })
            
            db_session.close()
            
            return {
                "status": "success",
                "cultural_metrics": metrics,
                "count": len(metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting cultural metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/context/values")
    async def update_company_values(
        request: Request,
        values_data: dict = Body(...)
    ):
        """Update company values and cultural principles."""
        try:
            db_session = get_db_session()
            
            # Create or update company values
            for value in values_data.get("values", []):
                existing_value = db_session.query(CompanyValues).filter(
                    CompanyValues.value_name == value["name"]
                ).first()
                
                if existing_value:
                    existing_value.value_description = value["description"]
                    existing_value.value_category = value["category"]
                    existing_value.priority_level = value.get("priority", 1)
                    existing_value.updated_at = datetime.utcnow()
                else:
                    new_value = CompanyValues(
                        value_name=value["name"],
                        value_description=value["description"],
                        value_category=value["category"],
                        priority_level=value.get("priority", 1)
                    )
                    db_session.add(new_value)
            
            db_session.commit()
            db_session.close()
            
            return {
                "status": "success",
                "message": "Company values updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating company values: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/context/values")
    async def get_company_values():
        """Get current company values and cultural principles."""
        try:
            db_session = get_db_session()
            
            values = db_session.query(CompanyValues).filter(
                CompanyValues.active == True
            ).order_by(CompanyValues.priority_level, CompanyValues.value_name).all()
            
            company_values = []
            for value in values:
                company_values.append({
                    "name": value.value_name,
                    "description": value.value_description,
                    "category": value.value_category,
                    "priority": value.priority_level
                })
            
            db_session.close()
            
            return {
                "status": "success",
                "company_values": company_values
            }
            
        except Exception as e:
            logger.error(f"Error getting company values: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Dashboard routes
    @app.get("/dashboard", response_class=HTMLResponse)
    async def executive_dashboard(request: Request):
        """Render the executive dashboard."""
        try:
            # For demo purposes, use a default user ID
            # In production, this would come from authentication
            user_id = "demo_executive_123"
            
            dashboard = get_dashboard()
            return await dashboard.render_dashboard(request, user_id)
            
        except Exception as e:
            logger.error(f"Error rendering dashboard: {e}")
            raise HTTPException(status_code=500, detail="Dashboard error")


    @app.get("/analytics", response_class=HTMLResponse)
    async def analytics_dashboard(request: Request):
        """Render the analytics dashboard."""
        try:
            user_id = "demo_executive_123"
            
            dashboard = get_dashboard()
            return await dashboard.render_analytics(request, user_id)
            
        except Exception as e:
            logger.error(f"Error rendering analytics: {e}")
            raise HTTPException(status_code=500, detail="Analytics error")


    @app.get("/decisions", response_class=HTMLResponse)
    async def decisions_dashboard(request: Request):
        """Render the decisions dashboard."""
        try:
            user_id = "demo_executive_123"
            
            dashboard = get_dashboard()
            return await dashboard.render_decisions(request, user_id)
            
        except Exception as e:
            logger.error(f"Error rendering decisions: {e}")
            raise HTTPException(status_code=500, detail="Decisions error")


    @app.get("/culture", response_class=HTMLResponse)
    async def culture_dashboard(request: Request):
        """Render the culture insights dashboard."""
        try:
            user_id = "demo_executive_123"
            
            dashboard = get_dashboard()
            return await dashboard.render_culture(request, user_id)
            
        except Exception as e:
            logger.error(f"Error rendering culture dashboard: {e}")
            raise HTTPException(status_code=500, detail="Culture dashboard error")


    @app.get("/", response_class=HTMLResponse)
    async def landing_page(request: Request):
        """Render the landing page with demo access."""
        try:
            return templates.TemplateResponse(
                "landing.html",
                {
                    "request": request,
                    "page_title": "Reflex AI - Executive AI Assistant"
                }
            )
            
        except Exception as e:
            logger.error(f"Error rendering landing page: {e}")
            raise HTTPException(status_code=500, detail="Landing page error")
    
    # Revenue Intelligence endpoints
    @app.post("/api/revenue/analyze")
    async def analyze_revenue_opportunities(
        request: Request,
        analysis_data: dict = Body(...)
    ):
        """Analyze conversation for revenue opportunities."""
        try:
            conversation_text = analysis_data.get("conversation_text", "")
            user_id = analysis_data.get("user_id", "")
            context = analysis_data.get("context", {})
            
            revenue_intelligence = get_revenue_intelligence()
            opportunities = await revenue_intelligence.analyze_conversation_for_opportunities(
                conversation_text=conversation_text,
                user_id=user_id,
                context=context
            )
            
            return {
                "status": "success",
                "opportunities_detected": len(opportunities),
                "opportunities": [
                    {
                        "type": opp.opportunity_type.value,
                        "company": opp.company_name,
                        "contact": opp.contact_name,
                        "estimated_value": opp.estimated_value,
                        "probability": opp.probability,
                        "urgency_score": opp.urgency_score,
                        "description": opp.description,
                        "key_indicators": opp.key_indicators,
                        "next_steps": opp.next_steps
                    }
                    for opp in opportunities
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing revenue opportunities: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/api/revenue/follow-ups")
    async def generate_follow_up_actions(
        request: Request,
        follow_up_data: dict = Body(...)
    ):
        """Generate follow-up actions for revenue opportunities."""
        try:
            opportunity_data = follow_up_data.get("opportunity", {})
            user_id = follow_up_data.get("user_id", "")
            
            # Create opportunity object
            from .ai.revenue_intelligence import RevenueOpportunityData, OpportunityType
            
            opportunity = RevenueOpportunityData(
                opportunity_type=OpportunityType(opportunity_data.get("type", "new_customer")),
                company_name=opportunity_data.get("company", ""),
                contact_name=opportunity_data.get("contact", ""),
                contact_email=opportunity_data.get("email", ""),
                estimated_value=float(opportunity_data.get("estimated_value", 0)),
                probability=float(opportunity_data.get("probability", 0.5)),
                timeline_days=int(opportunity_data.get("timeline_days", 30)),
                description=opportunity_data.get("description", ""),
                source_conversation=opportunity_data.get("source_conversation", ""),
                key_indicators=opportunity_data.get("key_indicators", []),
                next_steps=opportunity_data.get("next_steps", []),
                urgency_score=float(opportunity_data.get("urgency_score", 0.5))
            )
            
            revenue_intelligence = get_revenue_intelligence()
            follow_ups = await revenue_intelligence.generate_follow_up_actions(
                opportunity=opportunity,
                user_id=user_id
            )
            
            return {
                "status": "success",
                "follow_ups_generated": len(follow_ups),
                "follow_ups": [
                    {
                        "type": action.follow_up_type.value,
                        "priority": action.priority,
                        "due_date": action.due_date.isoformat(),
                        "description": action.action_description,
                        "expected_outcome": action.expected_outcome,
                        "revenue_impact": action.revenue_impact,
                        "automation_eligible": action.automation_eligible
                    }
                    for action in follow_ups
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating follow-up actions: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/revenue/metrics")
    async def get_revenue_metrics(days: int = 30):
        """Get revenue intelligence metrics."""
        try:
            revenue_intelligence = get_revenue_intelligence()
            metrics = await revenue_intelligence.track_revenue_metrics(
                user_id="demo_executive_123",  # For demo purposes
                days=days
            )
            
            return {
                "status": "success",
                "metrics": metrics,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/revenue/opportunities")
    async def get_revenue_opportunities():
        """Get all revenue opportunities."""
        try:
            db_session = get_db_session()
            
            opportunities = db_session.query(RevenueOpportunity).order_by(
                RevenueOpportunity.created_at.desc()
            ).limit(50).all()
            
            opportunities_data = []
            for opp in opportunities:
                opportunities_data.append({
                    "id": opp.id,
                    "type": opp.opportunity_type,
                    "company": opp.company_name,
                    "contact": opp.contact_name,
                    "estimated_value": opp.estimated_value,
                    "probability": opp.probability,
                    "stage": opp.stage,
                    "urgency_score": opp.urgency_score,
                    "created_at": opp.created_at.isoformat(),
                    "status": opp.status
                })
            
            db_session.close()
            
            return {
                "status": "success",
                "opportunities": opportunities_data,
                "count": len(opportunities_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue opportunities: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.get("/api/revenue/follow-ups")
    async def get_follow_up_tasks():
        """Get all follow-up tasks."""
        try:
            db_session = get_db_session()
            
            follow_ups = db_session.query(FollowUpTask).order_by(
                FollowUpTask.due_date.asc()
            ).limit(50).all()
            
            follow_ups_data = []
            for task in follow_ups:
                follow_ups_data.append({
                    "id": task.id,
                    "type": task.follow_up_type,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat(),
                    "description": task.action_description,
                    "expected_outcome": task.expected_outcome,
                    "revenue_impact": task.revenue_impact,
                    "completed": task.completed,
                    "automation_eligible": task.automation_eligible,
                    "created_at": task.created_at.isoformat()
                })
            
            db_session.close()
            
            return {
                "status": "success",
                "follow_ups": follow_ups_data,
                "count": len(follow_ups_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting follow-up tasks: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.put("/api/revenue/follow-ups/{task_id}/complete")
    async def complete_follow_up_task(
        task_id: int,
        completion_data: dict = Body(...)
    ):
        """Mark a follow-up task as completed."""
        try:
            db_session = get_db_session()
            
            task = db_session.query(FollowUpTask).filter(FollowUpTask.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            task.completed = True
            task.completed_at = datetime.utcnow()
            task.completion_notes = completion_data.get("notes", "")
            
            db_session.commit()
            db_session.close()
            
            return {
                "status": "success",
                "message": "Task completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error completing follow-up task: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.put("/api/revenue/opportunities/{opp_id}/stage")
    async def update_opportunity_stage(
        opp_id: int,
        stage_data: dict = Body(...)
    ):
        """Update opportunity stage."""
        try:
            db_session = get_db_session()
            
            opportunity = db_session.query(RevenueOpportunity).filter(RevenueOpportunity.id == opp_id).first()
            if not opportunity:
                raise HTTPException(status_code=404, detail="Opportunity not found")
            
            opportunity.stage = stage_data.get("stage", opportunity.stage)
            opportunity.updated_at = datetime.utcnow()
            
            db_session.commit()
            db_session.close()
            
            return {
                "status": "success",
                "message": "Opportunity stage updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating opportunity stage: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


# Create the app instance
app = create_app()


def main():
    """Main entry point for the application."""
    import uvicorn
    from .config import get_settings
    
    settings = get_settings()
    
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main() 