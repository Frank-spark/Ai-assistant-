"""Main tasks module for Reflex Executive Assistant."""

# Import all task modules
from . import email_tasks
from . import slack_tasks
from . import asana_tasks
from . import workflow_tasks
from . import maintenance_tasks

# Re-export commonly used tasks
__all__ = [
    # Email tasks
    "email_tasks",
    
    # Slack tasks
    "slack_tasks",
    
    # Asana tasks
    "asana_tasks",
    
    # Workflow tasks
    "workflow_tasks",
    
    # Maintenance tasks
    "maintenance_tasks",
] 