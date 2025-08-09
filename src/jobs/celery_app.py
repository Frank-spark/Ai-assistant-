"""Celery application configuration for Reflex Executive Assistant."""

import logging
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from ..config import get_settings

logger = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    settings = get_settings()
    
    # Create Celery app
    app = Celery(
        "reflex_assistant",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "src.jobs.tasks.email_tasks",
            "src.jobs.tasks.slack_tasks", 
            "src.jobs.tasks.asana_tasks",
            "src.jobs.tasks.workflow_tasks",
            "src.jobs.tasks.maintenance_tasks"
        ]
    )
    
    # Configure Celery
    app.conf.update(
        # Task routing
        task_routes={
            "src.jobs.tasks.email_tasks.*": {"queue": "email"},
            "src.jobs.tasks.slack_tasks.*": {"queue": "slack"},
            "src.jobs.tasks.asana_tasks.*": {"queue": "asana"},
            "src.jobs.tasks.workflow_tasks.*": {"queue": "workflow"},
            "src.jobs.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        },
        
        # Task serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # Worker settings
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        worker_disable_rate_limits=True,
        
        # Task execution
        task_always_eager=settings.celery_always_eager,
        task_eager_propagates=True,
        
        # Result backend
        result_expires=3600,  # 1 hour
        result_persistent=True,
        
        # Beat schedule (periodic tasks)
        beat_schedule={
            "sync-email": {
                "task": "src.jobs.tasks.email_tasks.sync_email",
                "schedule": crontab(minute="*/5"),  # Every 5 minutes
            },
            "sync-slack": {
                "task": "src.jobs.tasks.slack_tasks.sync_slack",
                "schedule": crontab(minute="*/2"),  # Every 2 minutes
            },
            "sync-asana": {
                "task": "src.jobs.tasks.asana_tasks.sync_asana",
                "schedule": crontab(minute="*/10"),  # Every 10 minutes
            },
            "cleanup-old-data": {
                "task": "src.jobs.tasks.maintenance_tasks.cleanup_old_data",
                "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
            },
            "update-knowledge-base": {
                "task": "src.jobs.tasks.maintenance_tasks.update_knowledge_base",
                "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
            },
            "health-check": {
                "task": "src.jobs.tasks.maintenance_tasks.health_check",
                "schedule": crontab(minute="*/15"),  # Every 15 minutes
            },
        },
        
        # Task routing
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
        
        # Error handling
        task_reject_on_worker_lost=True,
        task_acks_late=True,
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Security
        security_key=settings.celery_security_key,
        security_certificate=settings.celery_certificate,
        security_cert_store=settings.celery_cert_store,
    )
    
    # Configure logging
    app.conf.update(
        worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
        worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s"
    )
    
    logger.info("Celery application configured successfully")
    return app


# Create the Celery app instance
celery_app = create_celery_app()


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery configuration."""
    logger.info("Setting up periodic tasks")
    
    # Add any additional periodic task setup here
    # This can include dynamic task scheduling based on configuration


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    logger.info(f"Request: {self.request!r}")
    return "Debug task completed successfully"


if __name__ == "__main__":
    celery_app.start() 