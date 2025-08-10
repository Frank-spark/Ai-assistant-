"""Deep, durable integrations for Gmail, Slack, and Asana with high-fidelity connectors."""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from src.integrations.mcp_gateway import get_mcp_manager
from src.storage.models import Email, SlackMessage, AsanaTask, AsanaProject
from src.analytics.outcomes import OutcomesTracker

logger = logging.getLogger(__name__)


class IntegrationType(Enum):
    """Integration types."""
    GMAIL = "gmail"
    SLACK = "slack"
    ASANA = "asana"


@dataclass
class IntegrationConfig:
    """Configuration for deep integrations."""
    integration_type: IntegrationType
    enabled: bool
    auto_sync: bool
    sync_interval_minutes: int
    webhook_enabled: bool
    mcp_enabled: bool
    openapi_enabled: bool
    custom_mappings: Dict[str, Any]


class DeepGmailConnector:
    """High-fidelity Gmail integration with intelligent processing."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.mcp_manager = None
        self.auto_convert_rules = {
            "meeting_request": {
                "patterns": ["meeting", "call", "schedule", "calendar"],
                "action": "create_calendar_event",
                "priority": "high"
            },
            "task_request": {
                "patterns": ["task", "todo", "action item", "follow up"],
                "action": "create_asana_task",
                "priority": "medium"
            },
            "urgent_request": {
                "patterns": ["urgent", "asap", "emergency", "critical"],
                "action": "escalate",
                "priority": "critical"
            }
        }
    
    async def initialize(self):
        """Initialize the Gmail connector."""
        if self.config.mcp_enabled:
            self.mcp_manager = await get_mcp_manager()
    
    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email with intelligent routing and conversion."""
        
        # Extract email content
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        sender = email_data.get("from_email", "")
        labels = email_data.get("labels", "")
        
        # Analyze email content
        analysis = await self._analyze_email_content(subject, body, sender, labels)
        
        # Apply auto-conversion rules
        actions = await self._apply_auto_conversion_rules(analysis)
        
        # Create cross-platform actions
        cross_platform_actions = await self._create_cross_platform_actions(analysis, actions)
        
        return {
            "email_id": email_data.get("id"),
            "analysis": analysis,
            "actions": actions,
            "cross_platform_actions": cross_platform_actions,
            "processed_at": datetime.now().isoformat()
        }
    
    async def _analyze_email_content(self, subject: str, body: str, sender: str, labels: str) -> Dict[str, Any]:
        """Analyze email content for intelligent processing."""
        
        content = f"{subject} {body}".lower()
        
        analysis = {
            "intent": "unknown",
            "priority": "normal",
            "category": "general",
            "action_required": False,
            "deadline": None,
            "stakeholders": [],
            "topics": [],
            "sentiment": "neutral"
        }
        
        # Intent detection
        if any(word in content for word in ["meeting", "call", "schedule"]):
            analysis["intent"] = "meeting_request"
            analysis["action_required"] = True
        elif any(word in content for word in ["task", "todo", "action"]):
            analysis["intent"] = "task_request"
            analysis["action_required"] = True
        elif any(word in content for word in ["urgent", "asap", "emergency"]):
            analysis["intent"] = "urgent_request"
            analysis["priority"] = "high"
            analysis["action_required"] = True
        
        # Priority detection
        if any(word in content for word in ["urgent", "asap", "emergency", "critical"]):
            analysis["priority"] = "critical"
        elif any(word in content for word in ["important", "priority", "deadline"]):
            analysis["priority"] = "high"
        
        # Category detection
        if "sales" in content or "lead" in content:
            analysis["category"] = "sales"
        elif "support" in content or "help" in content:
            analysis["category"] = "support"
        elif "meeting" in content or "schedule" in content:
            analysis["category"] = "scheduling"
        
        # Deadline extraction
        deadline_keywords = ["due", "deadline", "by", "before", "until"]
        for keyword in deadline_keywords:
            if keyword in content:
                # Simple deadline extraction (in production, use NLP)
                analysis["deadline"] = "extracted_deadline"
                break
        
        return analysis
    
    async def _apply_auto_conversion_rules(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply auto-conversion rules based on email analysis."""
        
        actions = []
        
        for rule_name, rule in self.auto_convert_rules.items():
            if analysis["intent"] == rule_name or any(pattern in analysis.get("topics", []) for pattern in rule["patterns"]):
                action = {
                    "type": rule["action"],
                    "priority": rule["priority"],
                    "trigger": rule_name,
                    "data": analysis
                }
                actions.append(action)
        
        return actions
    
    async def _create_cross_platform_actions(self, analysis: Dict[str, Any], actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create cross-platform actions for the email."""
        
        cross_platform_actions = []
        
        for action in actions:
            if action["type"] == "create_calendar_event":
                cross_platform_actions.append({
                    "platform": "calendar",
                    "action": "create_event",
                    "data": {
                        "title": f"Meeting: {analysis.get('topics', ['General'])[0]}",
                        "attendees": analysis.get("stakeholders", []),
                        "priority": analysis["priority"]
                    }
                })
            
            elif action["type"] == "create_asana_task":
                cross_platform_actions.append({
                    "platform": "asana",
                    "action": "create_task",
                    "data": {
                        "name": f"Follow up: {analysis.get('topics', ['Action item'])[0]}",
                        "description": analysis.get("body", ""),
                        "priority": analysis["priority"],
                        "due_date": analysis.get("deadline")
                    }
                })
            
            elif action["type"] == "escalate":
                cross_platform_actions.append({
                    "platform": "slack",
                    "action": "send_alert",
                    "data": {
                        "channel": "urgent-alerts",
                        "message": f"Urgent request from {analysis.get('sender', 'Unknown')}",
                        "priority": "critical"
                    }
                })
        
        return cross_platform_actions


class DeepSlackConnector:
    """High-fidelity Slack integration with workflow automation."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.mcp_manager = None
        self.workflow_triggers = {
            "standup": {
                "patterns": ["standup", "daily", "update"],
                "action": "generate_standup_report",
                "channels": ["general", "engineering", "sales"]
            },
            "approval": {
                "patterns": ["approve", "approval", "sign off"],
                "action": "create_approval_workflow",
                "channels": ["management", "finance", "legal"]
            },
            "escalation": {
                "patterns": ["escalate", "urgent", "emergency"],
                "action": "escalate_to_manager",
                "channels": ["support", "operations"]
            }
        }
    
    async def initialize(self):
        """Initialize the Slack connector."""
        if self.config.mcp_enabled:
            self.mcp_manager = await get_mcp_manager()
    
    async def process_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Slack message with workflow automation."""
        
        text = message_data.get("text", "")
        channel = message_data.get("channel", "")
        user = message_data.get("user", "")
        
        # Analyze message content
        analysis = await self._analyze_message_content(text, channel, user)
        
        # Trigger workflows
        workflows = await self._trigger_workflows(analysis)
        
        # Create cross-platform actions
        cross_platform_actions = await self._create_cross_platform_actions(analysis, workflows)
        
        return {
            "message_id": message_data.get("id"),
            "analysis": analysis,
            "workflows": workflows,
            "cross_platform_actions": cross_platform_actions,
            "processed_at": datetime.now().isoformat()
        }
    
    async def _analyze_message_content(self, text: str, channel: str, user: str) -> Dict[str, Any]:
        """Analyze Slack message content."""
        
        content = text.lower()
        
        analysis = {
            "intent": "general",
            "workflow_trigger": None,
            "priority": "normal",
            "mentions": [],
            "topics": [],
            "sentiment": "neutral",
            "requires_action": False
        }
        
        # Check for workflow triggers
        for trigger_name, trigger in self.workflow_triggers.items():
            if any(pattern in content for pattern in trigger["patterns"]):
                analysis["workflow_trigger"] = trigger_name
                analysis["intent"] = trigger["action"]
                analysis["requires_action"] = True
        
        # Extract mentions
        if "<@" in text:
            mentions = text.split("<@")[1:]
            analysis["mentions"] = [mention.split(">")[0] for mention in mentions]
        
        # Priority detection
        if any(word in content for word in ["urgent", "asap", "emergency"]):
            analysis["priority"] = "high"
        
        return analysis
    
    async def _trigger_workflows(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Trigger workflows based on message analysis."""
        
        workflows = []
        
        if analysis["workflow_trigger"]:
            trigger = self.workflow_triggers[analysis["workflow_trigger"]]
            
            workflow = {
                "type": trigger["action"],
                "trigger": analysis["workflow_trigger"],
                "priority": analysis["priority"],
                "data": analysis
            }
            workflows.append(workflow)
        
        return workflows
    
    async def _create_cross_platform_actions(self, analysis: Dict[str, Any], workflows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create cross-platform actions for Slack messages."""
        
        cross_platform_actions = []
        
        for workflow in workflows:
            if workflow["type"] == "generate_standup_report":
                cross_platform_actions.append({
                    "platform": "asana",
                    "action": "create_project_update",
                    "data": {
                        "project": "Daily Standup",
                        "update": analysis.get("text", ""),
                        "participants": analysis.get("mentions", [])
                    }
                })
            
            elif workflow["type"] == "create_approval_workflow":
                cross_platform_actions.append({
                    "platform": "asana",
                    "action": "create_approval_task",
                    "data": {
                        "name": "Approval Required",
                        "description": analysis.get("text", ""),
                        "approvers": analysis.get("mentions", []),
                        "priority": analysis["priority"]
                    }
                })
        
        return cross_platform_actions


class DeepAsanaConnector:
    """High-fidelity Asana integration with project management automation."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.mcp_manager = None
        self.project_templates = {
            "product_launch": {
                "tasks": [
                    "Market research",
                    "Product requirements",
                    "Design mockups",
                    "Development",
                    "Testing",
                    "Marketing materials",
                    "Launch preparation"
                ],
                "dependencies": {
                    "Development": ["Design mockups"],
                    "Testing": ["Development"],
                    "Launch preparation": ["Testing", "Marketing materials"]
                }
            },
            "sales_campaign": {
                "tasks": [
                    "Target audience research",
                    "Campaign strategy",
                    "Content creation",
                    "Lead generation",
                    "Follow-up process",
                    "Performance tracking"
                ],
                "dependencies": {
                    "Content creation": ["Campaign strategy"],
                    "Lead generation": ["Content creation"],
                    "Follow-up process": ["Lead generation"]
                }
            }
        }
    
    async def initialize(self):
        """Initialize the Asana connector."""
        if self.config.mcp_enabled:
            self.mcp_manager = await get_mcp_manager()
    
    async def create_project_from_template(self, template_name: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create project from template with intelligent task creation."""
        
        if template_name not in self.project_templates:
            raise ValueError(f"Template {template_name} not found")
        
        template = self.project_templates[template_name]
        
        # Create project
        project = {
            "name": project_data.get("name", f"{template_name.title()} Project"),
            "description": project_data.get("description", ""),
            "template": template_name,
            "tasks": []
        }
        
        # Create tasks with dependencies
        for task_name in template["tasks"]:
            task = {
                "name": task_name,
                "description": f"Task for {task_name}",
                "assignee": project_data.get("assignee"),
                "due_date": project_data.get("due_date"),
                "dependencies": template["dependencies"].get(task_name, [])
            }
            project["tasks"].append(task)
        
        return project
    
    async def process_task_update(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Asana task updates with intelligent notifications."""
        
        task_id = task_data.get("id")
        task_name = task_data.get("name", "")
        status = task_data.get("status", "")
        assignee = task_data.get("assignee", "")
        
        # Analyze task update
        analysis = await self._analyze_task_update(task_data)
        
        # Create notifications
        notifications = await self._create_notifications(analysis)
        
        # Update related items
        updates = await self._update_related_items(analysis)
        
        return {
            "task_id": task_id,
            "analysis": analysis,
            "notifications": notifications,
            "updates": updates,
            "processed_at": datetime.now().isoformat()
        }
    
    async def _analyze_task_update(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Asana task update."""
        
        analysis = {
            "type": "update",
            "impact": "low",
            "stakeholders": [],
            "requires_notification": False,
            "blocks_others": False
        }
        
        # Check if task is completed
        if task_data.get("status") == "completed":
            analysis["type"] = "completion"
            analysis["impact"] = "high"
            analysis["requires_notification"] = True
        
        # Check if task is blocked
        if task_data.get("status") == "blocked":
            analysis["type"] = "blocked"
            analysis["impact"] = "medium"
            analysis["requires_notification"] = True
            analysis["blocks_others"] = True
        
        # Check for deadline changes
        if "due_date" in task_data:
            analysis["type"] = "deadline_change"
            analysis["impact"] = "medium"
            analysis["requires_notification"] = True
        
        return analysis
    
    async def _create_notifications(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create notifications based on task analysis."""
        
        notifications = []
        
        if analysis["requires_notification"]:
            if analysis["type"] == "completion":
                notifications.append({
                    "platform": "slack",
                    "channel": "project-updates",
                    "message": f"Task completed: {analysis.get('task_name', 'Unknown task')}",
                    "priority": "normal"
                })
            
            elif analysis["type"] == "blocked":
                notifications.append({
                    "platform": "slack",
                    "channel": "blocked-tasks",
                    "message": f"Task blocked: {analysis.get('task_name', 'Unknown task')} - requires attention",
                    "priority": "high"
                })
        
        return notifications
    
    async def _update_related_items(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update related items based on task analysis."""
        
        updates = []
        
        if analysis["type"] == "completion":
            # Unblock dependent tasks
            updates.append({
                "action": "unblock_dependent_tasks",
                "data": {
                    "completed_task": analysis.get("task_name"),
                    "dependent_tasks": analysis.get("dependent_tasks", [])
                }
            })
        
        return updates


class DeepIntegrationManager:
    """Manages deep, durable integrations across platforms."""
    
    def __init__(self):
        self.gmail_connector: Optional[DeepGmailConnector] = None
        self.slack_connector: Optional[DeepSlackConnector] = None
        self.asana_connector: Optional[DeepAsanaConnector] = None
        self.outcomes_tracker: Optional[OutcomesTracker] = None
    
    async def initialize(self, configs: Dict[str, IntegrationConfig]):
        """Initialize all deep connectors."""
        
        if IntegrationType.GMAIL in configs:
            self.gmail_connector = DeepGmailConnector(configs[IntegrationType.GMAIL])
            await self.gmail_connector.initialize()
        
        if IntegrationType.SLACK in configs:
            self.slack_connector = DeepSlackConnector(configs[IntegrationType.SLACK])
            await self.slack_connector.initialize()
        
        if IntegrationType.ASANA in configs:
            self.asana_connector = DeepAsanaConnector(configs[IntegrationType.ASANA])
            await self.asana_connector.initialize()
    
    async def process_gmail_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Gmail email with deep integration."""
        if not self.gmail_connector:
            raise RuntimeError("Gmail connector not initialized")
        
        result = await self.gmail_connector.process_email(email_data)
        
        # Execute cross-platform actions
        await self._execute_cross_platform_actions(result["cross_platform_actions"])
        
        return result
    
    async def process_slack_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Slack message with deep integration."""
        if not self.slack_connector:
            raise RuntimeError("Slack connector not initialized")
        
        result = await self.slack_connector.process_message(message_data)
        
        # Execute cross-platform actions
        await self._execute_cross_platform_actions(result["cross_platform_actions"])
        
        return result
    
    async def process_asana_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Asana task with deep integration."""
        if not self.asana_connector:
            raise RuntimeError("Asana connector not initialized")
        
        result = await self.asana_connector.process_task_update(task_data)
        
        # Execute cross-platform actions
        await self._execute_cross_platform_actions(result["cross_platform_actions"])
        
        return result
    
    async def _execute_cross_platform_actions(self, actions: List[Dict[str, Any]]):
        """Execute cross-platform actions."""
        
        for action in actions:
            try:
                if action["platform"] == "calendar":
                    await self._execute_calendar_action(action)
                elif action["platform"] == "asana":
                    await self._execute_asana_action(action)
                elif action["platform"] == "slack":
                    await self._execute_slack_action(action)
                
                logger.info(f"Executed cross-platform action: {action['action']}")
                
            except Exception as e:
                logger.error(f"Failed to execute cross-platform action: {e}")
    
    async def _execute_calendar_action(self, action: Dict[str, Any]):
        """Execute calendar action."""
        # Implementation for calendar actions
        pass
    
    async def _execute_asana_action(self, action: Dict[str, Any]):
        """Execute Asana action."""
        # Implementation for Asana actions
        pass
    
    async def _execute_slack_action(self, action: Dict[str, Any]):
        """Execute Slack action."""
        # Implementation for Slack actions
        pass 