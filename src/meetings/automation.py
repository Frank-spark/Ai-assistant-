"""Meeting automation with auto-transcription, summarization, and action-item capture."""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import re

from src.ai.chain import ReflexAIChain
from src.storage.models import Conversation, Message, WorkflowExecution
from src.analytics.outcomes import OutcomesTracker

logger = logging.getLogger(__name__)


class MeetingType(Enum):
    """Meeting types for different processing strategies."""
    STANDUP = "standup"
    BRAINSTORMING = "brainstorming"
    DECISION_MAKING = "decision_making"
    PROJECT_REVIEW = "project_review"
    CLIENT_MEETING = "client_meeting"
    BOARD_MEETING = "board_meeting"
    ONE_ON_ONE = "one_on_one"


@dataclass
class MeetingParticipant:
    """Meeting participant information."""
    name: str
    email: str
    role: str
    speaking_time: int = 0
    action_items: List[str] = None
    decisions: List[str] = None


@dataclass
class ActionItem:
    """Action item from meeting."""
    description: str
    assignee: str
    due_date: Optional[datetime]
    priority: str
    status: str
    context: str
    meeting_id: str


@dataclass
class MeetingDecision:
    """Decision made in meeting."""
    topic: str
    decision: str
    rationale: str
    stakeholders: List[str]
    follow_up_required: bool
    meeting_id: str


class MeetingTranscriber:
    """Handles real-time meeting transcription."""
    
    def __init__(self):
        self.speech_recognizer = None
        self.is_recording = False
        self.transcript_buffer = []
        self.speaker_diarization = {}
    
    async def start_transcription(self, meeting_id: str, participants: List[MeetingParticipant]):
        """Start real-time transcription."""
        self.is_recording = True
        self.meeting_id = meeting_id
        self.participants = participants
        
        # Initialize speech recognition
        await self._initialize_speech_recognition()
        
        logger.info(f"Started transcription for meeting {meeting_id}")
    
    async def stop_transcription(self) -> Dict[str, Any]:
        """Stop transcription and return results."""
        self.is_recording = False
        
        # Process final transcript
        final_transcript = await self._process_final_transcript()
        
        return {
            "meeting_id": self.meeting_id,
            "transcript": final_transcript,
            "speaker_diarization": self.speaker_diarization,
            "duration": self._calculate_duration(),
            "word_count": len(" ".join(final_transcript).split())
        }
    
    async def _initialize_speech_recognition(self):
        """Initialize speech recognition system."""
        # In production, integrate with real speech recognition API
        # For demo, simulate transcription
        pass
    
    async def _process_final_transcript(self) -> List[Dict[str, Any]]:
        """Process final transcript with speaker identification."""
        # Simulate transcript processing
        return [
            {
                "speaker": "Sarah Chen",
                "text": "Welcome everyone to our Q4 planning meeting.",
                "timestamp": "00:00:05",
                "confidence": 0.95
            },
            {
                "speaker": "Mike Rodriguez",
                "text": "Thanks Sarah. Let's start with our engineering priorities.",
                "timestamp": "00:00:15",
                "confidence": 0.92
            }
        ]
    
    def _calculate_duration(self) -> int:
        """Calculate meeting duration in seconds."""
        return 3600  # 1 hour for demo


class MeetingSummarizer:
    """Generates intelligent meeting summaries."""
    
    def __init__(self, ai_chain: ReflexAIChain):
        self.ai_chain = ai_chain
        self.summary_templates = {
            MeetingType.STANDUP: self._generate_standup_summary,
            MeetingType.BRAINSTORMING: self._generate_brainstorming_summary,
            MeetingType.DECISION_MAKING: self._generate_decision_summary,
            MeetingType.PROJECT_REVIEW: self._generate_project_summary,
            MeetingType.CLIENT_MEETING: self._generate_client_summary,
            MeetingType.BOARD_MEETING: self._generate_board_summary,
            MeetingType.ONE_ON_ONE: self._generate_one_on_one_summary
        }
    
    async def generate_summary(self, meeting_data: Dict[str, Any], meeting_type: MeetingType) -> Dict[str, Any]:
        """Generate meeting summary based on type."""
        
        template_func = self.summary_templates.get(meeting_type, self._generate_general_summary)
        summary = await template_func(meeting_data)
        
        return summary
    
    async def _generate_standup_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate standup meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        participants = meeting_data.get("participants", [])
        
        # Extract updates from each participant
        updates = {}
        blockers = []
        
        for participant in participants:
            participant_updates = []
            for entry in transcript:
                if entry.get("speaker") == participant.name:
                    text = entry.get("text", "")
                    if any(word in text.lower() for word in ["yesterday", "today", "blocked", "help"]):
                        participant_updates.append(text)
                        if "blocked" in text.lower():
                            blockers.append(f"{participant.name}: {text}")
            
            updates[participant.name] = participant_updates
        
        summary = {
            "type": "standup",
            "participant_updates": updates,
            "blockers": blockers,
            "next_actions": self._extract_next_actions(transcript),
            "key_metrics": self._extract_metrics(transcript)
        }
        
        return summary
    
    async def _generate_brainstorming_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate brainstorming meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        # Extract ideas and themes
        ideas = []
        themes = []
        
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["idea", "suggest", "propose", "think"]):
                ideas.append({
                    "speaker": entry.get("speaker"),
                    "idea": text,
                    "timestamp": entry.get("timestamp")
                })
        
        # Group ideas by themes
        themes = self._group_ideas_by_themes(ideas)
        
        summary = {
            "type": "brainstorming",
            "ideas": ideas,
            "themes": themes,
            "top_ideas": self._rank_ideas(ideas),
            "next_steps": self._extract_next_actions(transcript)
        }
        
        return summary
    
    async def _generate_decision_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate decision-making meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        # Extract decisions and rationale
        decisions = []
        context = []
        
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["decide", "decision", "agree", "approve"]):
                decisions.append({
                    "speaker": entry.get("speaker"),
                    "decision": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["because", "reason", "context"]):
                context.append({
                    "speaker": entry.get("speaker"),
                    "context": text,
                    "timestamp": entry.get("timestamp")
                })
        
        summary = {
            "type": "decision_making",
            "decisions": decisions,
            "context": context,
            "stakeholders": self._extract_stakeholders(transcript),
            "implementation_plan": self._extract_implementation_plan(transcript)
        }
        
        return summary
    
    async def _generate_project_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate project review meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        # Extract project updates
        progress_updates = []
        risks = []
        milestones = []
        
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["progress", "complete", "done", "finished"]):
                progress_updates.append({
                    "speaker": entry.get("speaker"),
                    "update": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["risk", "issue", "problem", "blocked"]):
                risks.append({
                    "speaker": entry.get("speaker"),
                    "risk": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["milestone", "deadline", "target"]):
                milestones.append({
                    "speaker": entry.get("speaker"),
                    "milestone": text,
                    "timestamp": entry.get("timestamp")
                })
        
        summary = {
            "type": "project_review",
            "progress_updates": progress_updates,
            "risks": risks,
            "milestones": milestones,
            "next_actions": self._extract_next_actions(transcript),
            "resource_needs": self._extract_resource_needs(transcript)
        }
        
        return summary
    
    async def _generate_client_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate client meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        # Extract client feedback and requirements
        feedback = []
        requirements = []
        next_steps = []
        
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["feedback", "like", "dislike", "concern"]):
                feedback.append({
                    "speaker": entry.get("speaker"),
                    "feedback": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["need", "require", "want", "expect"]):
                requirements.append({
                    "speaker": entry.get("speaker"),
                    "requirement": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["next", "follow", "schedule"]):
                next_steps.append({
                    "speaker": entry.get("speaker"),
                    "step": text,
                    "timestamp": entry.get("timestamp")
                })
        
        summary = {
            "type": "client_meeting",
            "client_feedback": feedback,
            "requirements": requirements,
            "next_steps": next_steps,
            "action_items": self._extract_action_items(transcript),
            "timeline": self._extract_timeline(transcript)
        }
        
        return summary
    
    async def _generate_board_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate board meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        # Extract board decisions and strategic items
        strategic_decisions = []
        financial_updates = []
        governance_items = []
        
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["strategy", "strategic", "direction"]):
                strategic_decisions.append({
                    "speaker": entry.get("speaker"),
                    "decision": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["financial", "revenue", "budget", "funding"]):
                financial_updates.append({
                    "speaker": entry.get("speaker"),
                    "update": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["governance", "policy", "compliance"]):
                governance_items.append({
                    "speaker": entry.get("speaker"),
                    "item": text,
                    "timestamp": entry.get("timestamp")
                })
        
        summary = {
            "type": "board_meeting",
            "strategic_decisions": strategic_decisions,
            "financial_updates": financial_updates,
            "governance_items": governance_items,
            "board_actions": self._extract_board_actions(transcript),
            "shareholder_communications": self._extract_shareholder_items(transcript)
        }
        
        return summary
    
    async def _generate_one_on_one_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate one-on-one meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        # Extract personal updates and development items
        personal_updates = []
        development_goals = []
        feedback = []
        
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["personal", "life", "family"]):
                personal_updates.append({
                    "speaker": entry.get("speaker"),
                    "update": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["goal", "development", "growth", "skill"]):
                development_goals.append({
                    "speaker": entry.get("speaker"),
                    "goal": text,
                    "timestamp": entry.get("timestamp")
                })
            elif any(word in text.lower() for word in ["feedback", "improve", "better"]):
                feedback.append({
                    "speaker": entry.get("speaker"),
                    "feedback": text,
                    "timestamp": entry.get("timestamp")
                })
        
        summary = {
            "type": "one_on_one",
            "personal_updates": personal_updates,
            "development_goals": development_goals,
            "feedback": feedback,
            "action_items": self._extract_action_items(transcript),
            "follow_up_topics": self._extract_follow_up_topics(transcript)
        }
        
        return summary
    
    async def _generate_general_summary(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate general meeting summary."""
        
        transcript = meeting_data.get("transcript", [])
        
        summary = {
            "type": "general",
            "key_points": self._extract_key_points(transcript),
            "action_items": self._extract_action_items(transcript),
            "decisions": self._extract_decisions(transcript),
            "participants": [entry.get("speaker") for entry in transcript if entry.get("speaker")],
            "duration": meeting_data.get("duration", 0)
        }
        
        return summary
    
    def _extract_next_actions(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract next actions from transcript."""
        actions = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["next", "action", "todo", "follow up"]):
                actions.append(text)
        return actions
    
    def _extract_metrics(self, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract key metrics from transcript."""
        metrics = {}
        for entry in transcript:
            text = entry.get("text", "")
            # Extract numbers and metrics
            numbers = re.findall(r'\d+', text)
            if numbers:
                metrics[entry.get("speaker", "unknown")] = numbers
        return metrics
    
    def _group_ideas_by_themes(self, ideas: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group ideas by themes."""
        themes = {}
        for idea in ideas:
            # Simple theme extraction (in production, use NLP)
            theme = "general"
            if "product" in idea["idea"].lower():
                theme = "product"
            elif "marketing" in idea["idea"].lower():
                theme = "marketing"
            elif "technical" in idea["idea"].lower():
                theme = "technical"
            
            if theme not in themes:
                themes[theme] = []
            themes[theme].append(idea["idea"])
        
        return themes
    
    def _rank_ideas(self, ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank ideas by importance."""
        # Simple ranking based on keywords
        ranked_ideas = []
        for idea in ideas:
            score = 0
            text = idea["idea"].lower()
            if "urgent" in text:
                score += 3
            if "important" in text:
                score += 2
            if "priority" in text:
                score += 2
            if "revenue" in text or "money" in text:
                score += 2
            
            ranked_ideas.append({
                **idea,
                "score": score
            })
        
        return sorted(ranked_ideas, key=lambda x: x["score"], reverse=True)
    
    def _extract_stakeholders(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract stakeholders from transcript."""
        stakeholders = set()
        for entry in transcript:
            text = entry.get("text", "")
            # Extract names (simple pattern matching)
            names = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', text)
            stakeholders.update(names)
        return list(stakeholders)
    
    def _extract_implementation_plan(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract implementation plan from transcript."""
        plan = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["implement", "execute", "plan", "timeline"]):
                plan.append(text)
        return plan
    
    def _extract_resource_needs(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract resource needs from transcript."""
        needs = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["need", "resource", "budget", "people"]):
                needs.append(text)
        return needs
    
    def _extract_action_items(self, transcript: List[Dict[str, Any]]) -> List[ActionItem]:
        """Extract action items from transcript."""
        action_items = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["action", "todo", "task", "follow up"]):
                action_item = ActionItem(
                    description=text,
                    assignee=entry.get("speaker", "Unknown"),
                    due_date=None,
                    priority="medium",
                    status="pending",
                    context="meeting",
                    meeting_id="demo-meeting"
                )
                action_items.append(action_item)
        return action_items
    
    def _extract_timeline(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract timeline items from transcript."""
        timeline = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["timeline", "schedule", "deadline", "when"]):
                timeline.append(text)
        return timeline
    
    def _extract_board_actions(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract board actions from transcript."""
        actions = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["approve", "vote", "resolution", "motion"]):
                actions.append(text)
        return actions
    
    def _extract_shareholder_items(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract shareholder communication items."""
        items = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["shareholder", "investor", "communication"]):
                items.append(text)
        return items
    
    def _extract_follow_up_topics(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract follow-up topics from transcript."""
        topics = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["follow up", "next time", "continue"]):
                topics.append(text)
        return topics
    
    def _extract_key_points(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract key points from transcript."""
        points = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["key", "important", "main", "critical"]):
                points.append(text)
        return points
    
    def _extract_decisions(self, transcript: List[Dict[str, Any]]) -> List[str]:
        """Extract decisions from transcript."""
        decisions = []
        for entry in transcript:
            text = entry.get("text", "")
            if any(word in text.lower() for word in ["decide", "decision", "agree", "approve"]):
                decisions.append(text)
        return decisions


class MeetingAutomation:
    """Main meeting automation orchestrator."""
    
    def __init__(self, ai_chain: ReflexAIChain):
        self.ai_chain = ai_chain
        self.transcriber = MeetingTranscriber()
        self.summarizer = MeetingSummarizer(ai_chain)
        self.outcomes_tracker = None
    
    async def start_meeting(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start meeting automation."""
        
        meeting_id = meeting_data.get("id")
        participants = [MeetingParticipant(**p) for p in meeting_data.get("participants", [])]
        meeting_type = MeetingType(meeting_data.get("type", "general"))
        
        # Start transcription
        await self.transcriber.start_transcription(meeting_id, participants)
        
        return {
            "meeting_id": meeting_id,
            "status": "started",
            "participants": len(participants),
            "type": meeting_type.value
        }
    
    async def end_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """End meeting and generate summary."""
        
        # Stop transcription
        transcript_data = await self.transcriber.stop_transcription()
        
        # Determine meeting type
        meeting_type = self._determine_meeting_type(transcript_data)
        
        # Generate summary
        summary = await self.summarizer.generate_summary(transcript_data, meeting_type)
        
        # Extract action items
        action_items = self._extract_action_items_from_summary(summary)
        
        # Create follow-up tasks
        follow_up_tasks = await self._create_follow_up_tasks(action_items, meeting_id)
        
        # Generate meeting report
        report = await self._generate_meeting_report(transcript_data, summary, action_items)
        
        return {
            "meeting_id": meeting_id,
            "transcript": transcript_data,
            "summary": summary,
            "action_items": action_items,
            "follow_up_tasks": follow_up_tasks,
            "report": report
        }
    
    def _determine_meeting_type(self, transcript_data: Dict[str, Any]) -> MeetingType:
        """Determine meeting type from transcript."""
        transcript = transcript_data.get("transcript", [])
        text = " ".join([entry.get("text", "") for entry in transcript]).lower()
        
        if any(word in text for word in ["standup", "daily", "update"]):
            return MeetingType.STANDUP
        elif any(word in text for word in ["brainstorm", "idea", "creative"]):
            return MeetingType.BRAINSTORMING
        elif any(word in text for word in ["decide", "decision", "approve"]):
            return MeetingType.DECISION_MAKING
        elif any(word in text for word in ["project", "review", "progress"]):
            return MeetingType.PROJECT_REVIEW
        elif any(word in text for word in ["client", "customer", "external"]):
            return MeetingType.CLIENT_MEETING
        elif any(word in text for word in ["board", "director", "governance"]):
            return MeetingType.BOARD_MEETING
        elif any(word in text for word in ["one on one", "1:1", "personal"]):
            return MeetingType.ONE_ON_ONE
        
        return MeetingType.STANDUP  # Default
    
    def _extract_action_items_from_summary(self, summary: Dict[str, Any]) -> List[ActionItem]:
        """Extract action items from meeting summary."""
        action_items = []
        
        # Extract from different summary types
        if "action_items" in summary:
            for item in summary["action_items"]:
                if isinstance(item, str):
                    action_item = ActionItem(
                        description=item,
                        assignee="Unknown",
                        due_date=None,
                        priority="medium",
                        status="pending",
                        context="meeting",
                        meeting_id="demo-meeting"
                    )
                    action_items.append(action_item)
                elif isinstance(item, dict):
                    action_item = ActionItem(
                        description=item.get("description", ""),
                        assignee=item.get("assignee", "Unknown"),
                        due_date=item.get("due_date"),
                        priority=item.get("priority", "medium"),
                        status=item.get("status", "pending"),
                        context="meeting",
                        meeting_id=item.get("meeting_id", "demo-meeting")
                    )
                    action_items.append(action_item)
        
        return action_items
    
    async def _create_follow_up_tasks(self, action_items: List[ActionItem], meeting_id: str) -> List[Dict[str, Any]]:
        """Create follow-up tasks from action items."""
        tasks = []
        
        for action_item in action_items:
            task = {
                "name": action_item.description,
                "description": f"Follow-up from meeting {meeting_id}",
                "assignee": action_item.assignee,
                "due_date": action_item.due_date,
                "priority": action_item.priority,
                "status": "pending",
                "source": "meeting_automation"
            }
            tasks.append(task)
        
        return tasks
    
    async def _generate_meeting_report(self, transcript_data: Dict[str, Any], summary: Dict[str, Any], action_items: List[ActionItem]) -> Dict[str, Any]:
        """Generate comprehensive meeting report."""
        
        report = {
            "meeting_id": transcript_data.get("meeting_id"),
            "duration": transcript_data.get("duration"),
            "participants": len(transcript_data.get("speaker_diarization", {})),
            "word_count": transcript_data.get("word_count"),
            "summary": summary,
            "action_items": [
                {
                    "description": item.description,
                    "assignee": item.assignee,
                    "due_date": item.due_date,
                    "priority": item.priority
                }
                for item in action_items
            ],
            "key_insights": self._extract_key_insights(summary),
            "next_steps": self._extract_next_steps(summary),
            "generated_at": datetime.now().isoformat()
        }
        
        return report
    
    def _extract_key_insights(self, summary: Dict[str, Any]) -> List[str]:
        """Extract key insights from meeting summary."""
        insights = []
        
        # Extract insights based on meeting type
        if summary.get("type") == "standup":
            if "blockers" in summary:
                insights.extend(summary["blockers"])
        
        elif summary.get("type") == "brainstorming":
            if "top_ideas" in summary:
                insights.extend([idea["idea"] for idea in summary["top_ideas"][:3]])
        
        elif summary.get("type") == "decision_making":
            if "decisions" in summary:
                insights.extend([decision["decision"] for decision in summary["decisions"]])
        
        return insights
    
    def _extract_next_steps(self, summary: Dict[str, Any]) -> List[str]:
        """Extract next steps from meeting summary."""
        next_steps = []
        
        if "next_actions" in summary:
            next_steps.extend(summary["next_actions"])
        
        if "next_steps" in summary:
            next_steps.extend(summary["next_steps"])
        
        return next_steps 