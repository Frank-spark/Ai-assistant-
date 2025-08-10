"""Visual workflow engine with rule chaining for non-developer users."""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import uuid

from src.storage.models import WorkflowExecution
from src.analytics.outcomes import OutcomesTracker

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Workflow trigger types."""
    EMAIL_RECEIVED = "email_received"
    SLACK_MESSAGE = "slack_message"
    ASANA_TASK_CREATED = "asana_task_created"
    ASANA_TASK_COMPLETED = "asana_task_completed"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class ActionType(Enum):
    """Workflow action types."""
    SEND_EMAIL = "send_email"
    CREATE_TASK = "create_task"
    SEND_SLACK_MESSAGE = "send_slack_message"
    UPDATE_ASANA_TASK = "update_asana_task"
    SCHEDULE_MEETING = "schedule_meeting"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    GENERATE_REPORT = "generate_report"
    SEND_NOTIFICATION = "send_notification"
    CONDITION = "condition"
    LOOP = "loop"
    DELAY = "delay"


class ConditionOperator(Enum):
    """Condition operators for workflow rules."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_EQUALS = "greater_than_equals"
    LESS_THAN_EQUALS = "less_than_equals"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass
class WorkflowTrigger:
    """Workflow trigger configuration."""
    id: str
    type: TriggerType
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class WorkflowCondition:
    """Workflow condition for branching logic."""
    id: str
    field: str
    operator: ConditionOperator
    value: Any
    description: str = ""


@dataclass
class WorkflowAction:
    """Workflow action configuration."""
    id: str
    type: ActionType
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    conditions: List[WorkflowCondition] = field(default_factory=list)
    enabled: bool = True
    position: Dict[str, int] = field(default_factory=dict)  # x, y coordinates for visual editor


@dataclass
class WorkflowConnection:
    """Connection between workflow elements."""
    id: str
    from_id: str
    to_id: str
    condition: Optional[WorkflowCondition] = None


@dataclass
class VisualWorkflow:
    """Complete visual workflow definition."""
    id: str
    name: str
    description: str
    trigger: WorkflowTrigger
    actions: List[WorkflowAction]
    connections: List[WorkflowConnection]
    variables: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class VisualWorkflowEngine:
    """Visual workflow engine for non-developer users."""
    
    def __init__(self):
        self.workflows: Dict[str, VisualWorkflow] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.outcomes_tracker = None
        
        # Pre-built workflow templates
        self.templates = self._create_workflow_templates()
    
    def _create_workflow_templates(self) -> Dict[str, VisualWorkflow]:
        """Create pre-built workflow templates."""
        
        templates = {}
        
        # Email to Task Template
        email_to_task = VisualWorkflow(
            id="email-to-task-template",
            name="Email to Task",
            description="Automatically create Asana tasks from important emails",
            trigger=WorkflowTrigger(
                id="email-trigger",
                type=TriggerType.EMAIL_RECEIVED,
                name="Email Received",
                description="Trigger when a new email is received",
                config={"filters": ["important", "urgent"]}
            ),
            actions=[
                WorkflowAction(
                    id="analyze-email",
                    type=ActionType.CONDITION,
                    name="Analyze Email",
                    description="Check if email requires action",
                    config={"field": "subject", "operator": "contains", "value": "action"}
                ),
                WorkflowAction(
                    id="create-task",
                    type=ActionType.CREATE_TASK,
                    name="Create Task",
                    description="Create Asana task from email",
                    config={
                        "project": "Inbox",
                        "name_template": "{{email.subject}}",
                        "description_template": "{{email.body}}"
                    }
                ),
                WorkflowAction(
                    id="send-notification",
                    type=ActionType.SEND_SLACK_MESSAGE,
                    name="Send Notification",
                    description="Notify team about new task",
                    config={
                        "channel": "tasks",
                        "message_template": "New task created: {{task.name}}"
                    }
                )
            ],
            connections=[
                WorkflowConnection("conn1", "email-trigger", "analyze-email"),
                WorkflowConnection("conn2", "analyze-email", "create-task"),
                WorkflowConnection("conn3", "create-task", "send-notification")
            ]
        )
        templates["email-to-task"] = email_to_task
        
        # Meeting Follow-up Template
        meeting_followup = VisualWorkflow(
            id="meeting-followup-template",
            name="Meeting Follow-up",
            description="Automatically create action items after meetings",
            trigger=WorkflowTrigger(
                id="meeting-trigger",
                type=TriggerType.SCHEDULED,
                name="Meeting Ended",
                description="Trigger when a meeting ends",
                config={"schedule": "after_meeting"}
            ),
            actions=[
                WorkflowAction(
                    id="generate-summary",
                    type=ActionType.GENERATE_REPORT,
                    name="Generate Summary",
                    description="Create meeting summary and action items",
                    config={"template": "meeting_summary"}
                ),
                WorkflowAction(
                    id="create-action-items",
                    type=ActionType.CREATE_TASK,
                    name="Create Action Items",
                    description="Create tasks for each action item",
                    config={"project": "Meeting Follow-ups"}
                ),
                WorkflowAction(
                    id="send-summary",
                    type=ActionType.SEND_EMAIL,
                    name="Send Summary",
                    description="Email summary to participants",
                    config={"template": "meeting_summary_email"}
                )
            ],
            connections=[
                WorkflowConnection("conn1", "meeting-trigger", "generate-summary"),
                WorkflowConnection("conn2", "generate-summary", "create-action-items"),
                WorkflowConnection("conn3", "create-action-items", "send-summary")
            ]
        )
        templates["meeting-followup"] = meeting_followup
        
        # Sales Lead Processing Template
        sales_lead = VisualWorkflow(
            id="sales-lead-template",
            name="Sales Lead Processing",
            description="Process new sales leads automatically",
            trigger=WorkflowTrigger(
                id="lead-trigger",
                type=TriggerType.EMAIL_RECEIVED,
                name="Lead Email",
                description="Trigger when a lead email is received",
                config={"filters": ["lead", "inquiry", "quote"]}
            ),
            actions=[
                WorkflowAction(
                    id="categorize-lead",
                    type=ActionType.CONDITION,
                    name="Categorize Lead",
                    description="Determine lead type and priority",
                    config={"field": "subject", "operator": "contains", "value": "enterprise"}
                ),
                WorkflowAction(
                    id="create-lead-task",
                    type=ActionType.CREATE_TASK,
                    name="Create Lead Task",
                    description="Create task for sales team",
                    config={"project": "Sales Pipeline", "priority": "high"}
                ),
                WorkflowAction(
                    id="schedule-followup",
                    type=ActionType.SCHEDULE_MEETING,
                    name="Schedule Follow-up",
                    description="Schedule sales call",
                    config={"duration": "30", "type": "sales_call"}
                ),
                WorkflowAction(
                    id="send-welcome",
                    type=ActionType.SEND_EMAIL,
                    name="Send Welcome",
                    description="Send welcome email to lead",
                    config={"template": "lead_welcome"}
                )
            ],
            connections=[
                WorkflowConnection("conn1", "lead-trigger", "categorize-lead"),
                WorkflowConnection("conn2", "categorize-lead", "create-lead-task"),
                WorkflowConnection("conn3", "create-lead-task", "schedule-followup"),
                WorkflowConnection("conn4", "schedule-followup", "send-welcome")
            ]
        )
        templates["sales-lead"] = sales_lead
        
        return templates
    
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> VisualWorkflow:
        """Create a new visual workflow."""
        
        workflow_id = str(uuid.uuid4())
        
        # Create trigger
        trigger_data = workflow_data.get("trigger", {})
        trigger = WorkflowTrigger(
            id=trigger_data.get("id", f"trigger-{workflow_id}"),
            type=TriggerType(trigger_data.get("type")),
            name=trigger_data.get("name", "New Trigger"),
            description=trigger_data.get("description", ""),
            config=trigger_data.get("config", {}),
            enabled=trigger_data.get("enabled", True)
        )
        
        # Create actions
        actions = []
        for action_data in workflow_data.get("actions", []):
            action = WorkflowAction(
                id=action_data.get("id", f"action-{len(actions)}"),
                type=ActionType(action_data.get("type")),
                name=action_data.get("name", "New Action"),
                description=action_data.get("description", ""),
                config=action_data.get("config", {}),
                conditions=[
                    WorkflowCondition(
                        id=cond.get("id", f"cond-{i}"),
                        field=cond.get("field", ""),
                        operator=ConditionOperator(cond.get("operator")),
                        value=cond.get("value"),
                        description=cond.get("description", "")
                    )
                    for i, cond in enumerate(action_data.get("conditions", []))
                ],
                enabled=action_data.get("enabled", True),
                position=action_data.get("position", {"x": 0, "y": 0})
            )
            actions.append(action)
        
        # Create connections
        connections = []
        for conn_data in workflow_data.get("connections", []):
            connection = WorkflowConnection(
                id=conn_data.get("id", f"conn-{len(connections)}"),
                from_id=conn_data.get("from_id"),
                to_id=conn_data.get("to_id"),
                condition=WorkflowCondition(
                    id=conn_data.get("condition", {}).get("id", f"conn-cond-{len(connections)}"),
                    field=conn_data.get("condition", {}).get("field", ""),
                    operator=ConditionOperator(conn_data.get("condition", {}).get("operator", "equals")),
                    value=conn_data.get("condition", {}).get("value"),
                    description=conn_data.get("condition", {}).get("description", "")
                ) if conn_data.get("condition") else None
            )
            connections.append(connection)
        
        # Create workflow
        workflow = VisualWorkflow(
            id=workflow_id,
            name=workflow_data.get("name", "New Workflow"),
            description=workflow_data.get("description", ""),
            trigger=trigger,
            actions=actions,
            connections=connections,
            variables=workflow_data.get("variables", {}),
            enabled=workflow_data.get("enabled", True)
        )
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {workflow.name} ({workflow_id})")
        
        return workflow
    
    async def execute_workflow(self, workflow_id: str, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a visual workflow."""
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        if not workflow.enabled:
            raise ValueError(f"Workflow {workflow_id} is disabled")
        
        execution_id = str(uuid.uuid4())
        execution_start = datetime.now()
        
        # Initialize execution context
        context = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "trigger_data": trigger_data,
            "variables": workflow.variables.copy(),
            "results": {},
            "errors": [],
            "start_time": execution_start
        }
        
        try:
            # Execute workflow
            result = await self._execute_workflow_steps(workflow, context)
            
            # Record execution
            execution_record = {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "completed" if not context["errors"] else "failed",
                "start_time": execution_start,
                "end_time": datetime.now(),
                "duration": (datetime.now() - execution_start).total_seconds(),
                "results": context["results"],
                "errors": context["errors"]
            }
            
            self.execution_history.append(execution_record)
            
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            context["errors"].append(str(e))
            
            execution_record = {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "failed",
                "start_time": execution_start,
                "end_time": datetime.now(),
                "duration": (datetime.now() - execution_start).total_seconds(),
                "results": context["results"],
                "errors": context["errors"]
            }
            
            self.execution_history.append(execution_record)
            raise
    
    async def _execute_workflow_steps(self, workflow: VisualWorkflow, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow steps in order."""
        
        # Start with trigger
        current_step_id = workflow.trigger.id
        executed_steps = []
        
        while current_step_id:
            # Find next step
            next_step = self._find_next_step(workflow, current_step_id, context)
            
            if not next_step:
                break
            
            # Execute step
            step_result = await self._execute_step(next_step, context)
            context["results"][next_step.id] = step_result
            executed_steps.append(next_step.id)
            
            # Move to next step
            current_step_id = next_step.id
        
        return {
            "execution_id": context["execution_id"],
            "workflow_id": workflow.id,
            "executed_steps": executed_steps,
            "results": context["results"],
            "errors": context["errors"]
        }
    
    def _find_next_step(self, workflow: VisualWorkflow, current_step_id: str, context: Dict[str, Any]) -> Optional[WorkflowAction]:
        """Find the next step to execute."""
        
        # Find connections from current step
        connections = [conn for conn in workflow.connections if conn.from_id == current_step_id]
        
        if not connections:
            return None
        
        # For now, take the first connection (in production, evaluate conditions)
        next_connection = connections[0]
        
        # Find the action
        next_action = next((action for action in workflow.actions if action.id == next_connection.to_id), None)
        
        return next_action
    
    async def _execute_step(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step."""
        
        try:
            # Check conditions
            if not await self._evaluate_conditions(action.conditions, context):
                return {"status": "skipped", "reason": "conditions_not_met"}
            
            # Execute action based on type
            if action.type == ActionType.SEND_EMAIL:
                result = await self._execute_send_email(action, context)
            elif action.type == ActionType.CREATE_TASK:
                result = await self._execute_create_task(action, context)
            elif action.type == ActionType.SEND_SLACK_MESSAGE:
                result = await self._execute_send_slack_message(action, context)
            elif action.type == ActionType.UPDATE_ASANA_TASK:
                result = await self._execute_update_asana_task(action, context)
            elif action.type == ActionType.SCHEDULE_MEETING:
                result = await self._execute_schedule_meeting(action, context)
            elif action.type == ActionType.CREATE_CALENDAR_EVENT:
                result = await self._execute_create_calendar_event(action, context)
            elif action.type == ActionType.GENERATE_REPORT:
                result = await self._execute_generate_report(action, context)
            elif action.type == ActionType.SEND_NOTIFICATION:
                result = await self._execute_send_notification(action, context)
            elif action.type == ActionType.CONDITION:
                result = await self._execute_condition(action, context)
            elif action.type == ActionType.LOOP:
                result = await self._execute_loop(action, context)
            elif action.type == ActionType.DELAY:
                result = await self._execute_delay(action, context)
            else:
                result = {"status": "unknown_action_type", "action_type": action.type.value}
            
            return result
            
        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            context["errors"].append(f"Step {action.id}: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _evaluate_conditions(self, conditions: List[WorkflowCondition], context: Dict[str, Any]) -> bool:
        """Evaluate workflow conditions."""
        
        if not conditions:
            return True
        
        for condition in conditions:
            # Get field value from context
            field_value = self._get_field_value(condition.field, context)
            
            # Evaluate condition
            if not self._evaluate_condition(condition, field_value):
                return False
        
        return True
    
    def _get_field_value(self, field: str, context: Dict[str, Any]) -> Any:
        """Get field value from context using dot notation."""
        
        keys = field.split(".")
        value = context
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _evaluate_condition(self, condition: WorkflowCondition, field_value: Any) -> bool:
        """Evaluate a single condition."""
        
        if condition.operator == ConditionOperator.EQUALS:
            return field_value == condition.value
        elif condition.operator == ConditionOperator.NOT_EQUALS:
            return field_value != condition.value
        elif condition.operator == ConditionOperator.CONTAINS:
            return condition.value in str(field_value) if field_value else False
        elif condition.operator == ConditionOperator.NOT_CONTAINS:
            return condition.value not in str(field_value) if field_value else True
        elif condition.operator == ConditionOperator.GREATER_THAN:
            return field_value > condition.value if field_value else False
        elif condition.operator == ConditionOperator.LESS_THAN:
            return field_value < condition.value if field_value else False
        elif condition.operator == ConditionOperator.GREATER_THAN_EQUALS:
            return field_value >= condition.value if field_value else False
        elif condition.operator == ConditionOperator.LESS_THAN_EQUALS:
            return field_value <= condition.value if field_value else False
        elif condition.operator == ConditionOperator.IS_EMPTY:
            return not field_value or field_value == ""
        elif condition.operator == ConditionOperator.IS_NOT_EMPTY:
            return field_value and field_value != ""
        
        return False
    
    async def _execute_send_email(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send email action."""
        # Implementation for sending email
        return {"status": "completed", "action": "send_email"}
    
    async def _execute_create_task(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create task action."""
        # Implementation for creating task
        return {"status": "completed", "action": "create_task"}
    
    async def _execute_send_slack_message(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send Slack message action."""
        # Implementation for sending Slack message
        return {"status": "completed", "action": "send_slack_message"}
    
    async def _execute_update_asana_task(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute update Asana task action."""
        # Implementation for updating Asana task
        return {"status": "completed", "action": "update_asana_task"}
    
    async def _execute_schedule_meeting(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute schedule meeting action."""
        # Implementation for scheduling meeting
        return {"status": "completed", "action": "schedule_meeting"}
    
    async def _execute_create_calendar_event(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create calendar event action."""
        # Implementation for creating calendar event
        return {"status": "completed", "action": "create_calendar_event"}
    
    async def _execute_generate_report(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute generate report action."""
        # Implementation for generating report
        return {"status": "completed", "action": "generate_report"}
    
    async def _execute_send_notification(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send notification action."""
        # Implementation for sending notification
        return {"status": "completed", "action": "send_notification"}
    
    async def _execute_condition(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute condition action."""
        # Implementation for condition evaluation
        return {"status": "completed", "action": "condition"}
    
    async def _execute_loop(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute loop action."""
        # Implementation for loop execution
        return {"status": "completed", "action": "loop"}
    
    async def _execute_delay(self, action: WorkflowAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delay action."""
        # Implementation for delay
        delay_seconds = action.config.get("delay_seconds", 0)
        await asyncio.sleep(delay_seconds)
        return {"status": "completed", "action": "delay", "delay_seconds": delay_seconds}
    
    def get_workflow_templates(self) -> Dict[str, VisualWorkflow]:
        """Get available workflow templates."""
        return self.templates
    
    def get_workflow(self, workflow_id: str) -> Optional[VisualWorkflow]:
        """Get a specific workflow."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        return [
            {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "enabled": workflow.enabled,
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at
            }
            for workflow in self.workflows.values()
        ]
    
    def get_execution_history(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get execution history."""
        history = self.execution_history
        
        if workflow_id:
            history = [record for record in history if record["workflow_id"] == workflow_id]
        
        return history 