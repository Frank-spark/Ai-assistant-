"""Main FastAPI application for Reflex Executive Assistant."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
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
from .kb.retriever import init_kb_retriever
from .web.dashboard import router as dashboard_router
from .web.landing import router as landing_router
from .saas.auth import router as auth_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global state
ai_chain = None
kb_retriever = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global ai_chain, kb_retriever
    
    # Startup
    logger.info("Starting Reflex Executive Assistant...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize Celery
        init_celery()
        logger.info("Celery initialized successfully")
        
        # Initialize knowledge base retriever
        kb_retriever = init_kb_retriever()
        logger.info("Knowledge base retriever initialized successfully")
        
        # Initialize AI chain
        ai_chain = init_ai_chain(kb_retriever)
        logger.info("AI chain initialized successfully")
        
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
            "version": "0.1.0"
        }
    
    @app.get("/healthz")
    async def health_check_detailed() -> Dict[str, Any]:
        """Detailed health check endpoint."""
        return {
            "status": "healthy",
            "service": "reflex-executive-assistant",
            "version": "0.1.0"
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