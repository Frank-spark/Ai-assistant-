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

from .config import get_settings, is_production
from .logging.setup import setup_logging
from .storage.db import init_db, close_db
from .jobs.queue import init_celery, close_celery
from .integrations.webhooks import slack_router, gmail_router, asana_router
from .workflows.router import workflow_router
from .ai.chain import init_ai_chain
from .ai.model_switcher import init_model_switcher
from .ai.ceo_vision_chain import init_ceo_vision_chain
from .kb.retriever import init_kb_retriever
from .kb.enhanced_retriever import init_enhanced_kb_retriever
from .analytics.telemetry import init_telemetry_service
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