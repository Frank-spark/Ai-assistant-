"""Multi-step autonomous agents for high autonomous workflow execution."""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import uuid

from src.ai.chain import ReflexAIChain
from src.storage.models import WorkflowExecution, Conversation, Message
from src.analytics.outcomes import OutcomesTracker

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Autonomous agent types."""
    TRIAGE_AGENT = "triage_agent"
    SCHEDULING_AGENT = "scheduling_agent"
    FOLLOW_UP_AGENT = "follow_up_agent"
    ESCALATION_AGENT = "escalation_agent"
    DECISION_AGENT = "decision_agent"
    RESEARCH_AGENT = "research_agent"


class ApprovalStatus(Enum):
    """Approval status for autonomous actions."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    ESCALATED = "escalated"


class ActionPriority(Enum):
    """Action priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AutonomousAction:
    """Autonomous action definition."""
    id: str
    agent_type: AgentType
    action_type: str
    description: str
    priority: ActionPriority
    data: Dict[str, Any]
    requires_approval: bool = True
    approval_threshold: float = 0.8
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"


@dataclass
class ApprovalRequest:
    """Approval request for autonomous actions."""
    id: str
    action_id: str
    requester_id: str
    approver_id: str
    action_description: str
    priority: ActionPriority
    data: Dict[str, Any]
    confidence_score: float
    reasoning: str
    created_at: datetime = field(default_factory=datetime.now)
    status: ApprovalStatus = ApprovalStatus.PENDING
    response_time: Optional[datetime] = None
    response_reason: Optional[str] = None


class TriageAgent:
    """Autonomous agent for intelligent triage and routing."""
    
    def __init__(self, ai_chain: ReflexAIChain):
        self.ai_chain = ai_chain
        self.triage_rules = {
            "urgent": {
                "keywords": ["urgent", "asap", "emergency", "critical"],
                "priority": ActionPriority.CRITICAL,
                "auto_approval": False,
                "escalation_time": 5  # minutes
            },
            "high_priority": {
                "keywords": ["important", "priority", "deadline"],
                "priority": ActionPriority.HIGH,
                "auto_approval": False,
                "escalation_time": 30  # minutes
            },
            "routine": {
                "keywords": ["follow up", "update", "check"],
                "priority": ActionPriority.MEDIUM,
                "auto_approval": True,
                "escalation_time": 120  # minutes
            },
            "low_priority": {
                "keywords": ["general", "info", "question"],
                "priority": ActionPriority.LOW,
                "auto_approval": True,
                "escalation_time": 480  # minutes
            }
        }
    
    async def triage_input(self, input_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Triage input and determine appropriate action."""
        
        content = input_data.get("content", "")
        source = input_data.get("source", "unknown")
        
        # Analyze content for triage
        analysis = await self._analyze_content(content)
        
        # Determine priority and action
        triage_result = await self._determine_triage_action(analysis, source, user_id)
        
        # Create autonomous action
        action = AutonomousAction(
            id=str(uuid.uuid4()),
            agent_type=AgentType.TRIAGE_AGENT,
            action_type="triage_and_route",
            description=f"Triage {source} input: {analysis['category']}",
            priority=triage_result["priority"],
            data={
                "input_data": input_data,
                "analysis": analysis,
                "triage_result": triage_result
            },
            requires_approval=triage_result["requires_approval"]
        )
        
        return {
            "action": action,
            "analysis": analysis,
            "triage_result": triage_result,
            "next_steps": triage_result["next_steps"]
        }
    
    async def _analyze_content(self, content: str) -> Dict[str, Any]:
        """Analyze content for triage classification."""
        
        content_lower = content.lower()
        
        analysis = {
            "category": "routine",
            "urgency_score": 0,
            "complexity_score": 0,
            "keywords": [],
            "entities": [],
            "sentiment": "neutral"
        }
        
        # Check for urgency indicators
        for category, rule in self.triage_rules.items():
            for keyword in rule["keywords"]:
                if keyword in content_lower:
                    analysis["keywords"].append(keyword)
                    analysis["urgency_score"] += 1
                    
                    if category == "urgent":
                        analysis["category"] = "urgent"
                        analysis["urgency_score"] += 3
                    elif category == "high_priority" and analysis["category"] != "urgent":
                        analysis["category"] = "high_priority"
                        analysis["urgency_score"] += 2
        
        # Check for complexity indicators
        complexity_indicators = ["complex", "detailed", "analysis", "research", "investigation"]
        for indicator in complexity_indicators:
            if indicator in content_lower:
                analysis["complexity_score"] += 1
        
        # Determine sentiment
        positive_words = ["good", "great", "excellent", "positive", "success"]
        negative_words = ["bad", "terrible", "problem", "issue", "failure"]
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            analysis["sentiment"] = "positive"
        elif negative_count > positive_count:
            analysis["sentiment"] = "negative"
        
        return analysis
    
    async def _determine_triage_action(self, analysis: Dict[str, Any], source: str, user_id: str) -> Dict[str, Any]:
        """Determine appropriate triage action."""
        
        category = analysis["category"]
        urgency_score = analysis["urgency_score"]
        
        # Get triage rule
        rule = self.triage_rules.get(category, self.triage_rules["routine"])
        
        # Determine priority
        if urgency_score >= 5:
            priority = ActionPriority.CRITICAL
        elif urgency_score >= 3:
            priority = ActionPriority.HIGH
        elif urgency_score >= 1:
            priority = ActionPriority.MEDIUM
        else:
            priority = ActionPriority.LOW
        
        # Determine if auto-approval is allowed
        requires_approval = rule["auto_approval"] == False
        
        # Determine next steps
        next_steps = []
        
        if category == "urgent":
            next_steps.extend([
                "immediate_notification",
                "escalation_to_manager",
                "priority_handling"
            ])
        elif category == "high_priority":
            next_steps.extend([
                "quick_response",
                "dedicated_handling"
            ])
        elif category == "routine":
            next_steps.extend([
                "standard_processing",
                "queue_for_handling"
            ])
        else:
            next_steps.append("general_processing")
        
        return {
            "priority": priority,
            "requires_approval": requires_approval,
            "escalation_time": rule["escalation_time"],
            "next_steps": next_steps,
            "assigned_agent": self._determine_assigned_agent(analysis, source)
        }
    
    def _determine_assigned_agent(self, analysis: Dict[str, Any], source: str) -> str:
        """Determine which agent should handle the request."""
        
        if analysis["category"] == "urgent":
            return "escalation_agent"
        elif "schedule" in analysis["keywords"] or "meeting" in analysis["keywords"]:
            return "scheduling_agent"
        elif "follow up" in analysis["keywords"] or "check" in analysis["keywords"]:
            return "follow_up_agent"
        elif analysis["complexity_score"] > 2:
            return "research_agent"
        else:
            return "decision_agent"


class SchedulingAgent:
    """Autonomous agent for intelligent scheduling."""
    
    def __init__(self, ai_chain: ReflexAIChain):
        self.ai_chain = ai_chain
        self.scheduling_rules = {
            "meeting_duration": {
                "default": 30,
                "keywords": {
                    "quick": 15,
                    "brief": 15,
                    "detailed": 60,
                    "comprehensive": 90
                }
            },
            "priority_handling": {
                "urgent": {"max_wait": 2, "auto_approval": False},
                "high": {"max_wait": 24, "auto_approval": True},
                "medium": {"max_wait": 72, "auto_approval": True},
                "low": {"max_wait": 168, "auto_approval": True}
            }
        }
    
    async def schedule_meeting(self, request_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Autonomously schedule a meeting."""
        
        # Analyze scheduling request
        analysis = await self._analyze_scheduling_request(request_data)
        
        # Determine meeting parameters
        meeting_params = await self._determine_meeting_parameters(analysis)
        
        # Check availability and find slots
        available_slots = await self._find_available_slots(meeting_params, user_id)
        
        # Select optimal slot
        selected_slot = await self._select_optimal_slot(available_slots, analysis)
        
        # Create scheduling action
        action = AutonomousAction(
            id=str(uuid.uuid4()),
            agent_type=AgentType.SCHEDULING_AGENT,
            action_type="schedule_meeting",
            description=f"Schedule {meeting_params['type']} meeting",
            priority=analysis["priority"],
            data={
                "request_data": request_data,
                "analysis": analysis,
                "meeting_params": meeting_params,
                "selected_slot": selected_slot
            },
            requires_approval=analysis["requires_approval"]
        )
        
        return {
            "action": action,
            "analysis": analysis,
            "meeting_params": meeting_params,
            "selected_slot": selected_slot,
            "next_steps": ["send_invites", "update_calendar", "send_confirmation"]
        }
    
    async def _analyze_scheduling_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze scheduling request for parameters."""
        
        content = request_data.get("content", "")
        participants = request_data.get("participants", [])
        
        analysis = {
            "type": "general",
            "duration": 30,
            "priority": ActionPriority.MEDIUM,
            "participants": participants,
            "requires_approval": False,
            "constraints": []
        }
        
        # Determine meeting type
        content_lower = content.lower()
        if "interview" in content_lower:
            analysis["type"] = "interview"
            analysis["duration"] = 60
        elif "presentation" in content_lower:
            analysis["type"] = "presentation"
            analysis["duration"] = 45
        elif "brainstorm" in content_lower:
            analysis["type"] = "brainstorming"
            analysis["duration"] = 60
        elif "quick" in content_lower or "brief" in content_lower:
            analysis["duration"] = 15
        elif "detailed" in content_lower:
            analysis["duration"] = 90
        
        # Determine priority
        if "urgent" in content_lower or "asap" in content_lower:
            analysis["priority"] = ActionPriority.CRITICAL
            analysis["requires_approval"] = False
        elif "important" in content_lower:
            analysis["priority"] = ActionPriority.HIGH
        
        # Extract constraints
        if "morning" in content_lower:
            analysis["constraints"].append("morning_only")
        if "afternoon" in content_lower:
            analysis["constraints"].append("afternoon_only")
        if "this week" in content_lower:
            analysis["constraints"].append("this_week")
        
        return analysis
    
    async def _determine_meeting_parameters(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine meeting parameters."""
        
        return {
            "type": analysis["type"],
            "duration": analysis["duration"],
            "participants": analysis["participants"],
            "constraints": analysis["constraints"],
            "priority": analysis["priority"]
        }
    
    async def _find_available_slots(self, meeting_params: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
        """Find available time slots."""
        
        # In production, this would query calendar APIs
        # For demo, generate sample slots
        slots = []
        base_time = datetime.now() + timedelta(hours=1)
        
        for i in range(5):
            slot_time = base_time + timedelta(hours=i*2)
            slots.append({
                "start_time": slot_time,
                "end_time": slot_time + timedelta(minutes=meeting_params["duration"]),
                "available": True,
                "score": 100 - (i * 10)  # Earlier slots get higher scores
            })
        
        return slots
    
    async def _select_optimal_slot(self, slots: List[Dict[str, Any]], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Select optimal time slot."""
        
        if not slots:
            return None
        
        # For urgent requests, take the earliest slot
        if analysis["priority"] == ActionPriority.CRITICAL:
            return min(slots, key=lambda x: x["start_time"])
        
        # Otherwise, take the highest scoring slot
        return max(slots, key=lambda x: x["score"])


class FollowUpAgent:
    """Autonomous agent for intelligent follow-ups."""
    
    def __init__(self, ai_chain: ReflexAIChain):
        self.ai_chain = ai_chain
        self.follow_up_templates = {
            "meeting": {
                "subject": "Follow-up: {{meeting_title}}",
                "body": "Hi {{recipient}},\n\nFollowing up on our meeting about {{topic}}. Here are the key points and action items:\n\n{{action_items}}\n\nNext steps:\n{{next_steps}}\n\nLet me know if you need any clarification.\n\nBest regards,\n{{sender}}"
            },
            "task": {
                "subject": "Task Update: {{task_name}}",
                "body": "Hi {{recipient}},\n\nI wanted to check in on the task: {{task_name}}\n\nCurrent status: {{status}}\n\nAny blockers or updates?\n\nThanks,\n{{sender}}"
            },
            "general": {
                "subject": "Follow-up: {{topic}}",
                "body": "Hi {{recipient}},\n\nFollowing up on {{topic}}.\n\n{{message}}\n\nBest regards,\n{{sender}}"
            }
        }
    
    async def create_follow_up(self, context_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Create intelligent follow-up."""
        
        # Analyze follow-up context
        analysis = await self._analyze_follow_up_context(context_data)
        
        # Generate follow-up content
        follow_up_content = await self._generate_follow_up_content(analysis)
        
        # Determine follow-up timing
        timing = await self._determine_follow_up_timing(analysis)
        
        # Create follow-up action
        action = AutonomousAction(
            id=str(uuid.uuid4()),
            agent_type=AgentType.FOLLOW_UP_AGENT,
            action_type="create_follow_up",
            description=f"Follow up on {analysis['type']}",
            priority=analysis["priority"],
            data={
                "context_data": context_data,
                "analysis": analysis,
                "follow_up_content": follow_up_content,
                "timing": timing
            },
            requires_approval=analysis["requires_approval"]
        )
        
        return {
            "action": action,
            "analysis": analysis,
            "follow_up_content": follow_up_content,
            "timing": timing,
            "next_steps": ["schedule_follow_up", "send_reminder", "track_response"]
        }
    
    async def _analyze_follow_up_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze follow-up context."""
        
        context_type = context_data.get("type", "general")
        urgency = context_data.get("urgency", "normal")
        participants = context_data.get("participants", [])
        
        analysis = {
            "type": context_type,
            "urgency": urgency,
            "participants": participants,
            "priority": ActionPriority.MEDIUM,
            "requires_approval": False,
            "template": self.follow_up_templates.get(context_type, self.follow_up_templates["general"])
        }
        
        # Determine priority based on urgency
        if urgency == "urgent":
            analysis["priority"] = ActionPriority.HIGH
        elif urgency == "critical":
            analysis["priority"] = ActionPriority.CRITICAL
            analysis["requires_approval"] = True
        
        return analysis
    
    async def _generate_follow_up_content(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate follow-up content."""
        
        template = analysis["template"]
        
        # In production, this would use AI to generate personalized content
        # For demo, use template with placeholders
        content = {
            "subject": template["subject"],
            "body": template["body"],
            "recipients": analysis["participants"],
            "cc": [],
            "bcc": []
        }
        
        return content
    
    async def _determine_follow_up_timing(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal follow-up timing."""
        
        timing_rules = {
            "urgent": {"delay_hours": 2, "reminder_hours": 24},
            "high": {"delay_hours": 24, "reminder_hours": 72},
            "medium": {"delay_hours": 72, "reminder_hours": 168},
            "low": {"delay_hours": 168, "reminder_hours": 336}
        }
        
        urgency = analysis["urgency"]
        rule = timing_rules.get(urgency, timing_rules["medium"])
        
        return {
            "delay_hours": rule["delay_hours"],
            "reminder_hours": rule["reminder_hours"],
            "scheduled_time": datetime.now() + timedelta(hours=rule["delay_hours"])
        }


class ApprovalManager:
    """Manages approval workflows for autonomous actions."""
    
    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []
        self.auto_approval_threshold = 0.8
    
    async def create_approval_request(self, action: AutonomousAction, user_id: str) -> ApprovalRequest:
        """Create approval request for autonomous action."""
        
        # Determine approver
        approver_id = await self._determine_approver(action, user_id)
        
        # Calculate confidence score
        confidence_score = await self._calculate_confidence_score(action)
        
        # Generate reasoning
        reasoning = await self._generate_approval_reasoning(action)
        
        # Create approval request
        approval_request = ApprovalRequest(
            id=str(uuid.uuid4()),
            action_id=action.id,
            requester_id=user_id,
            approver_id=approver_id,
            action_description=action.description,
            priority=action.priority,
            data=action.data,
            confidence_score=confidence_score,
            reasoning=reasoning
        )
        
        # Check if auto-approval is possible
        if confidence_score >= self.auto_approval_threshold and not action.requires_approval:
            approval_request.status = ApprovalStatus.AUTO_APPROVED
            approval_request.response_time = datetime.now()
            approval_request.response_reason = "Auto-approved based on high confidence score"
        else:
            self.pending_approvals[approval_request.id] = approval_request
        
        self.approval_history.append(approval_request)
        
        return approval_request
    
    async def _determine_approver(self, action: AutonomousAction, user_id: str) -> str:
        """Determine appropriate approver for action."""
        
        # In production, this would check organizational hierarchy
        # For demo, return a default approver
        return "manager@company.com"
    
    async def _calculate_confidence_score(self, action: AutonomousAction) -> float:
        """Calculate confidence score for action."""
        
        # In production, this would use AI to analyze the action
        # For demo, return a high confidence score
        base_score = 0.7
        
        # Adjust based on action type
        if action.agent_type == AgentType.TRIAGE_AGENT:
            base_score += 0.1
        elif action.agent_type == AgentType.SCHEDULING_AGENT:
            base_score += 0.15
        elif action.agent_type == AgentType.FOLLOW_UP_AGENT:
            base_score += 0.05
        
        # Adjust based on priority
        if action.priority == ActionPriority.LOW:
            base_score += 0.1
        elif action.priority == ActionPriority.CRITICAL:
            base_score -= 0.1
        
        return min(max(base_score, 0.0), 1.0)
    
    async def _generate_approval_reasoning(self, action: AutonomousAction) -> str:
        """Generate reasoning for approval request."""
        
        reasoning_templates = {
            AgentType.TRIAGE_AGENT: "This input has been classified as {priority} priority and requires {action_type}.",
            AgentType.SCHEDULING_AGENT: "A meeting has been scheduled based on the request with {participants} participants.",
            AgentType.FOLLOW_UP_AGENT: "A follow-up has been created for {context} with {recipients} recipients."
        }
        
        template = reasoning_templates.get(action.agent_type, "Autonomous action requires approval.")
        
        return template.format(
            priority=action.priority.value,
            action_type=action.action_type,
            participants=len(action.data.get("participants", [])),
            context=action.data.get("context", "general"),
            recipients=len(action.data.get("recipients", []))
        )
    
    async def approve_action(self, approval_id: str, approver_id: str, reason: str = "") -> bool:
        """Approve an action."""
        
        if approval_id not in self.pending_approvals:
            return False
        
        approval_request = self.pending_approvals[approval_id]
        
        if approval_request.approver_id != approver_id:
            return False
        
        approval_request.status = ApprovalStatus.APPROVED
        approval_request.response_time = datetime.now()
        approval_request.response_reason = reason or "Approved by approver"
        
        del self.pending_approvals[approval_id]
        
        return True
    
    async def reject_action(self, approval_id: str, approver_id: str, reason: str) -> bool:
        """Reject an action."""
        
        if approval_id not in self.pending_approvals:
            return False
        
        approval_request = self.pending_approvals[approval_id]
        
        if approval_request.approver_id != approver_id:
            return False
        
        approval_request.status = ApprovalStatus.REJECTED
        approval_request.response_time = datetime.now()
        approval_request.response_reason = reason
        
        del self.pending_approvals[approval_id]
        
        return True
    
    def get_pending_approvals(self, approver_id: str) -> List[ApprovalRequest]:
        """Get pending approvals for an approver."""
        
        return [
            approval for approval in self.pending_approvals.values()
            if approval.approver_id == approver_id
        ]
    
    def get_approval_history(self, user_id: str) -> List[ApprovalRequest]:
        """Get approval history for a user."""
        
        return [
            approval for approval in self.approval_history
            if approval.requester_id == user_id or approval.approver_id == user_id
        ]


class AutonomousWorkflowManager:
    """Manages autonomous workflow execution."""
    
    def __init__(self, ai_chain: ReflexAIChain):
        self.ai_chain = ai_chain
        self.triage_agent = TriageAgent(ai_chain)
        self.scheduling_agent = SchedulingAgent(ai_chain)
        self.follow_up_agent = FollowUpAgent(ai_chain)
        self.approval_manager = ApprovalManager()
        self.outcomes_tracker = None
        
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: List[Dict[str, Any]] = []
    
    async def process_input(self, input_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Process input through autonomous workflow."""
        
        workflow_id = str(uuid.uuid4())
        
        # Step 1: Triage
        triage_result = await self.triage_agent.triage_input(input_data, user_id)
        
        # Step 2: Create approval request if needed
        approval_request = None
        if triage_result["action"].requires_approval:
            approval_request = await self.approval_manager.create_approval_request(
                triage_result["action"], user_id
            )
        
        # Step 3: Execute or queue action
        if approval_request and approval_request.status == ApprovalStatus.PENDING:
            # Queue for approval
            self.active_workflows[workflow_id] = {
                "workflow_id": workflow_id,
                "user_id": user_id,
                "status": "pending_approval",
                "triage_result": triage_result,
                "approval_request": approval_request,
                "created_at": datetime.now()
            }
            
            return {
                "workflow_id": workflow_id,
                "status": "pending_approval",
                "approval_request": approval_request,
                "next_steps": ["wait_for_approval"]
            }
        else:
            # Execute immediately
            execution_result = await self._execute_workflow(triage_result, user_id)
            
            self.workflow_history.append({
                "workflow_id": workflow_id,
                "user_id": user_id,
                "status": "completed",
                "triage_result": triage_result,
                "execution_result": execution_result,
                "created_at": datetime.now(),
                "completed_at": datetime.now()
            })
            
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "execution_result": execution_result
            }
    
    async def _execute_workflow(self, triage_result: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Execute autonomous workflow."""
        
        action = triage_result["action"]
        assigned_agent = triage_result["triage_result"]["assigned_agent"]
        
        execution_result = {
            "action_id": action.id,
            "agent_type": action.agent_type.value,
            "assigned_agent": assigned_agent,
            "steps_completed": [],
            "results": {}
        }
        
        # Execute based on assigned agent
        if assigned_agent == "scheduling_agent":
            result = await self.scheduling_agent.schedule_meeting(action.data, user_id)
            execution_result["steps_completed"].append("scheduling")
            execution_result["results"]["scheduling"] = result
        
        elif assigned_agent == "follow_up_agent":
            result = await self.follow_up_agent.create_follow_up(action.data, user_id)
            execution_result["steps_completed"].append("follow_up")
            execution_result["results"]["follow_up"] = result
        
        elif assigned_agent == "escalation_agent":
            # Handle escalation
            execution_result["steps_completed"].append("escalation")
            execution_result["results"]["escalation"] = {
                "status": "escalated",
                "escalated_to": "manager@company.com"
            }
        
        else:
            # Default handling
            execution_result["steps_completed"].append("general_processing")
            execution_result["results"]["general"] = {
                "status": "processed",
                "message": "Input processed successfully"
            }
        
        return execution_result
    
    async def approve_workflow(self, workflow_id: str, approver_id: str, reason: str = "") -> Dict[str, Any]:
        """Approve a pending workflow."""
        
        if workflow_id not in self.active_workflows:
            return {"error": "Workflow not found"}
        
        workflow = self.active_workflows[workflow_id]
        approval_request = workflow["approval_request"]
        
        # Approve the action
        success = await self.approval_manager.approve_action(
            approval_request.id, approver_id, reason
        )
        
        if success:
            # Execute the workflow
            execution_result = await self._execute_workflow(
                workflow["triage_result"], workflow["user_id"]
            )
            
            # Update workflow status
            workflow["status"] = "completed"
            workflow["execution_result"] = execution_result
            workflow["completed_at"] = datetime.now()
            
            # Move to history
            self.workflow_history.append(workflow)
            del self.active_workflows[workflow_id]
            
            return {
                "workflow_id": workflow_id,
                "status": "approved_and_executed",
                "execution_result": execution_result
            }
        else:
            return {"error": "Approval failed"}
    
    def get_active_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active workflows for user."""
        
        return [
            workflow for workflow in self.active_workflows.values()
            if workflow["user_id"] == user_id
        ]
    
    def get_workflow_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get workflow history for user."""
        
        return [
            workflow for workflow in self.workflow_history
            if workflow["user_id"] == user_id
        ]
    
    def get_pending_approvals(self, approver_id: str) -> List[ApprovalRequest]:
        """Get pending approvals for approver."""
        
        return self.approval_manager.get_pending_approvals(approver_id) 