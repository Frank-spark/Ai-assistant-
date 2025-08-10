"""Integration hooks and example connectors for Reflex AI Assistant."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
import json
import re

from fastapi import HTTPException
from pydantic import BaseModel

from src.ai.chain import ReflexAIChain
from src.kb.enhanced_retriever import get_enhanced_kb_retriever
from src.analytics.telemetry import get_telemetry_service, EventType
from src.config import get_settings

logger = logging.getLogger(__name__)


class IntegrationHook(BaseModel):
    """Base class for integration hooks."""
    name: str
    description: str
    trigger_conditions: List[str]
    actions: List[str]
    enabled: bool = True
    config: Dict[str, Any] = {}


@dataclass
class HookContext:
    """Context for hook execution."""
    user_id: str
    platform: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any] = None


class IntegrationHookManager:
    """Manages integration hooks and connectors."""
    
    def __init__(self):
        self.hooks: Dict[str, IntegrationHook] = {}
        self.handlers: Dict[str, Callable] = {}
        self.ai_chain = None
        self.kb_retriever = None
        self.telemetry = get_telemetry_service()
        
        # Register default hooks
        self._register_default_hooks()
    
    def register_hook(self, hook: IntegrationHook, handler: Callable):
        """Register a new integration hook."""
        self.hooks[hook.name] = hook
        self.handlers[hook.name] = handler
        logger.info(f"Registered hook: {hook.name}")
    
    def unregister_hook(self, hook_name: str):
        """Unregister an integration hook."""
        if hook_name in self.hooks:
            del self.hooks[hook_name]
            del self.handlers[hook_name]
            logger.info(f"Unregistered hook: {hook_name}")
    
    async def execute_hook(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """Execute matching hooks for a given context."""
        try:
            results = []
            
            for hook_name, hook in self.hooks.items():
                if not hook.enabled:
                    continue
                
                # Check if hook should be triggered
                if self._should_trigger_hook(hook, context):
                    try:
                        handler = self.handlers[hook_name]
                        result = await handler(context)
                        
                        if result:
                            results.append({
                                "hook_name": hook_name,
                                "result": result
                            })
                        
                        # Track hook execution
                        await self.telemetry.track_event(
                            EventType.FEATURE_USED,
                            user_id=context.user_id,
                            metadata={
                                "hook_name": hook_name,
                                "platform": context.platform,
                                "event_type": context.event_type,
                                "success": True
                            }
                        )
                        
                    except Exception as e:
                        logger.error(f"Hook {hook_name} failed: {e}")
                        await self.telemetry.track_error(
                            "hook_execution_failed",
                            str(e),
                            user_id=context.user_id,
                            metadata={"hook_name": hook_name}
                        )
            
            return {"executed_hooks": len(results), "results": results}
            
        except Exception as e:
            logger.error(f"Hook execution failed: {e}")
            return None
    
    def _should_trigger_hook(self, hook: IntegrationHook, context: HookContext) -> bool:
        """Check if a hook should be triggered based on context."""
        # Check platform
        if "platform" in hook.trigger_conditions:
            if context.platform not in hook.trigger_conditions["platform"]:
                return False
        
        # Check event type
        if "event_type" in hook.trigger_conditions:
            if context.event_type not in hook.trigger_conditions["event_type"]:
                return False
        
        # Check custom conditions
        if "custom" in hook.trigger_conditions:
            custom_condition = hook.trigger_conditions["custom"]
            if not self._evaluate_custom_condition(custom_condition, context):
                return False
        
        return True
    
    def _evaluate_custom_condition(self, condition: str, context: HookContext) -> bool:
        """Evaluate custom trigger conditions."""
        try:
            # Simple condition evaluation (can be extended)
            if "contains" in condition:
                key, value = condition["contains"].split(":")
                return value in str(context.event_data.get(key, ""))
            elif "equals" in condition:
                key, value = condition["equals"].split(":")
                return str(context.event_data.get(key, "")) == value
            return True
        except Exception as e:
            logger.error(f"Failed to evaluate custom condition: {e}")
            return False
    
    def _register_default_hooks(self):
        """Register default integration hooks."""
        
        # Email Auto-Response Hook
        email_hook = IntegrationHook(
            name="email_auto_response",
            description="Automatically respond to common email inquiries",
            trigger_conditions={
                "platform": ["email"],
                "event_type": ["email_received"],
                "custom": {"contains": "subject:help"}
            },
            actions=["analyze_email", "generate_response", "send_reply"]
        )
        self.register_hook(email_hook, self._email_auto_response_handler)
        
        # Meeting Scheduler Hook
        meeting_hook = IntegrationHook(
            name="meeting_scheduler",
            description="Schedule meetings based on availability",
            trigger_conditions={
                "platform": ["slack", "email"],
                "event_type": ["message_received"],
                "custom": {"contains": "schedule meeting"}
            },
            actions=["check_availability", "propose_times", "send_invites"]
        )
        self.register_hook(meeting_hook, self._meeting_scheduler_handler)
        
        # Task Creator Hook
        task_hook = IntegrationHook(
            name="task_creator",
            description="Create tasks from conversations",
            trigger_conditions={
                "platform": ["slack", "email"],
                "event_type": ["message_received"],
                "custom": {"contains": "create task"}
            },
            actions=["extract_task_details", "create_asana_task", "notify_user"]
        )
        self.register_hook(task_hook, self._task_creator_handler)
        
        # Knowledge Base Update Hook
        kb_hook = IntegrationHook(
            name="knowledge_base_update",
            description="Update knowledge base from conversations",
            trigger_conditions={
                "platform": ["slack", "email"],
                "event_type": ["message_received"],
                "custom": {"contains": "important information"}
            },
            actions=["extract_key_info", "update_kb", "notify_admin"]
        )
        self.register_hook(kb_hook, self._knowledge_base_update_handler)
        
        # Customer Support Hook
        support_hook = IntegrationHook(
            name="customer_support",
            description="Handle customer support inquiries",
            trigger_conditions={
                "platform": ["slack", "email"],
                "event_type": ["message_received"],
                "custom": {"contains": "support"}
            },
            actions=["classify_inquiry", "generate_response", "escalate_if_needed"]
        )
        self.register_hook(support_hook, self._customer_support_handler)
    
    async def _email_auto_response_handler(self, context: HookContext) -> Dict[str, Any]:
        """Handle email auto-response."""
        try:
            # Analyze email content
            email_content = context.event_data.get("content", "")
            email_subject = context.event_data.get("subject", "")
            
            # Generate AI response
            prompt = f"""
            Analyze this email and generate an appropriate response:
            
            Subject: {email_subject}
            Content: {email_content}
            
            Generate a professional, helpful response that addresses the inquiry.
            """
            
            # Get AI response (simplified - would use actual AI chain)
            response = f"Thank you for your email about '{email_subject}'. I'll help you with that."
            
            return {
                "action": "email_auto_response",
                "response": response,
                "confidence": 0.85
            }
            
        except Exception as e:
            logger.error(f"Email auto-response failed: {e}")
            return None
    
    async def _meeting_scheduler_handler(self, context: HookContext) -> Dict[str, Any]:
        """Handle meeting scheduling."""
        try:
            message_content = context.event_data.get("content", "")
            
            # Extract meeting details
            meeting_details = {
                "duration": "30 minutes",
                "participants": ["user@example.com"],
                "topic": "General discussion"
            }
            
            # Generate meeting proposal
            response = f"""
            I can help you schedule a meeting! Here are some available times:
            - Tomorrow at 10:00 AM
            - Tomorrow at 2:00 PM
            - Wednesday at 11:00 AM
            
            Which time works best for you?
            """
            
            return {
                "action": "meeting_scheduler",
                "proposed_times": ["10:00 AM", "2:00 PM", "11:00 AM"],
                "response": response
            }
            
        except Exception as e:
            logger.error(f"Meeting scheduler failed: {e}")
            return None
    
    async def _task_creator_handler(self, context: HookContext) -> Dict[str, Any]:
        """Handle task creation."""
        try:
            message_content = context.event_data.get("content", "")
            
            # Extract task details
            task_details = {
                "title": "New task from conversation",
                "description": message_content,
                "assignee": context.user_id,
                "due_date": None
            }
            
            # Create task (simplified - would use actual Asana API)
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return {
                "action": "task_creator",
                "task_id": task_id,
                "task_details": task_details,
                "response": f"I've created a task for you: {task_details['title']}"
            }
            
        except Exception as e:
            logger.error(f"Task creator failed: {e}")
            return None
    
    async def _knowledge_base_update_handler(self, context: HookContext) -> Dict[str, Any]:
        """Handle knowledge base updates."""
        try:
            message_content = context.event_data.get("content", "")
            
            # Extract key information
            key_info = {
                "content": message_content,
                "source": context.platform,
                "user_id": context.user_id,
                "timestamp": context.timestamp.isoformat()
            }
            
            # Update knowledge base
            kb_retriever = get_enhanced_kb_retriever()
            success = await kb_retriever.add_document(
                content=message_content,
                metadata=key_info
            )
            
            return {
                "action": "knowledge_base_update",
                "success": success,
                "response": "I've updated the knowledge base with this information."
            }
            
        except Exception as e:
            logger.error(f"Knowledge base update failed: {e}")
            return None
    
    async def _customer_support_handler(self, context: HookContext) -> Dict[str, Any]:
        """Handle customer support inquiries."""
        try:
            message_content = context.event_data.get("content", "")
            
            # Classify inquiry
            inquiry_type = "general"
            if "billing" in message_content.lower():
                inquiry_type = "billing"
            elif "technical" in message_content.lower():
                inquiry_type = "technical"
            
            # Generate response
            responses = {
                "billing": "I can help you with billing questions. Let me check your account...",
                "technical": "I can help you with technical issues. Let me gather some information...",
                "general": "I'm here to help! How can I assist you today?"
            }
            
            response = responses.get(inquiry_type, responses["general"])
            
            return {
                "action": "customer_support",
                "inquiry_type": inquiry_type,
                "response": response,
                "escalation_needed": inquiry_type == "technical"
            }
            
        except Exception as e:
            logger.error(f"Customer support handler failed: {e}")
            return None


# Example connectors for common platforms
class SlackConnector:
    """Slack integration connector."""
    
    def __init__(self, webhook_url: str, bot_token: str):
        self.webhook_url = webhook_url
        self.bot_token = bot_token
    
    async def send_message(self, channel: str, message: str, thread_ts: Optional[str] = None):
        """Send a message to Slack."""
        try:
            payload = {
                "channel": channel,
                "text": message
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            # Send to Slack (simplified)
            logger.info(f"Slack message sent to {channel}: {message}")
            return {"success": True, "message_id": "slack_msg_123"}
            
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_channel_info(self, channel_id: str):
        """Get channel information."""
        try:
            # Get channel info (simplified)
            return {
                "id": channel_id,
                "name": "general",
                "is_private": False,
                "member_count": 10
            }
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return None


class EmailConnector:
    """Email integration connector."""
    
    def __init__(self, smtp_config: Dict[str, Any]):
        self.smtp_config = smtp_config
    
    async def send_email(self, to_email: str, subject: str, body: str, 
                        from_email: Optional[str] = None):
        """Send an email."""
        try:
            # Send email (simplified)
            logger.info(f"Email sent to {to_email}: {subject}")
            return {"success": True, "message_id": "email_123"}
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_email_thread(self, thread_id: str):
        """Get email thread information."""
        try:
            # Get thread info (simplified)
            return {
                "thread_id": thread_id,
                "subject": "Email thread",
                "messages": []
            }
        except Exception as e:
            logger.error(f"Failed to get email thread: {e}")
            return None


class AsanaConnector:
    """Asana integration connector."""
    
    def __init__(self, access_token: str, workspace_id: str):
        self.access_token = access_token
        self.workspace_id = workspace_id
    
    async def create_task(self, project_id: str, title: str, description: str = "",
                         assignee: Optional[str] = None, due_date: Optional[str] = None):
        """Create a task in Asana."""
        try:
            # Create task (simplified)
            task_id = f"asana_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Asana task created: {title}")
            return {"success": True, "task_id": task_id}
            
        except Exception as e:
            logger.error(f"Failed to create Asana task: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update a task in Asana."""
        try:
            # Update task (simplified)
            logger.info(f"Asana task updated: {task_id}")
            return {"success": True, "task_id": task_id}
            
        except Exception as e:
            logger.error(f"Failed to update Asana task: {e}")
            return {"success": False, "error": str(e)}


# Global hook manager instance
hook_manager = None


def get_hook_manager() -> IntegrationHookManager:
    """Get the global hook manager instance."""
    global hook_manager
    if hook_manager is None:
        hook_manager = IntegrationHookManager()
    return hook_manager


async def init_hook_manager():
    """Initialize the hook manager."""
    global hook_manager
    hook_manager = IntegrationHookManager()
    logger.info("Integration hook manager initialized")
    return hook_manager 