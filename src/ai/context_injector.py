"""Strategic Context Injection System for Reflex Executive Assistant."""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI

from ..config import get_settings
from ..storage.models import StrategicContext, CompanyValues, TeamAlignment
from ..storage.db import get_db_session
from ..kb.enhanced_retriever import get_enhanced_kb_retriever
from ..analytics.telemetry import get_telemetry_service, EventType

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of strategic context to inject."""
    VALUES = "values"
    GOALS = "goals"
    CULTURE = "culture"
    STRATEGY = "strategy"
    WELL_BEING = "well_being"
    DIVERSITY = "diversity"
    LEADERSHIP = "leadership"


class CommunicationChannel(Enum):
    """Communication channels for context injection."""
    SLACK = "slack"
    EMAIL = "email"
    ASANA = "asana"
    CALENDAR = "calendar"
    MEETING = "meeting"
    DOCUMENT = "document"


@dataclass
class StrategicContextData:
    """Strategic context data for injection."""
    company_values: List[str]
    current_goals: Dict[str, Any]
    cultural_principles: List[str]
    strategic_priorities: List[str]
    well_being_focus: List[str]
    diversity_commitments: List[str]
    leadership_style: str
    last_updated: datetime


@dataclass
class ContextInjection:
    """Context injection configuration."""
    context_type: ContextType
    channel: CommunicationChannel
    content: str
    original_message: str
    injected_context: str
    alignment_score: float
    cultural_relevance: float


class StrategicContextInjector:
    """AI-powered system for injecting strategic context into communications."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.model_name,
            temperature=0.1,
            openai_api_key=self.settings.openai_api_key
        )
        self.kb_retriever = get_enhanced_kb_retriever()
        self.telemetry = get_telemetry_service()
        
        # Context injection rules
        self.injection_rules = {
            CommunicationChannel.SLACK: {
                "frequency": "selective",  # Only when relevant
                "style": "natural",
                "max_length": 100
            },
            CommunicationChannel.EMAIL: {
                "frequency": "always",
                "style": "professional",
                "max_length": 200
            },
            CommunicationChannel.ASANA: {
                "frequency": "task_relevant",
                "style": "actionable",
                "max_length": 150
            },
            CommunicationChannel.MEETING: {
                "frequency": "agenda_relevant",
                "style": "conversational",
                "max_length": 100
            }
        }
        
        # Cultural sensitivity settings
        self.cultural_sensitivity = {
            "inclusive_language": True,
            "well_being_awareness": True,
            "diversity_respect": True,
            "leadership_empathy": True
        }
        
        logger.info("Strategic Context Injector initialized")
    
    async def inject_context(
        self,
        content: str,
        channel: CommunicationChannel,
        user_id: str,
        team_id: str = None
    ) -> ContextInjection:
        """Inject strategic context into communication content."""
        try:
            logger.info(f"Injecting context into {channel.value} communication")
            
            # Get current strategic context
            strategic_context = await self._get_current_strategic_context()
            
            # Analyze content for context relevance
            relevance_analysis = await self._analyze_context_relevance(
                content, strategic_context
            )
            
            # Determine if context injection is needed
            if not self._should_inject_context(channel, relevance_analysis):
                return ContextInjection(
                    context_type=ContextType.STRATEGY,
                    channel=channel,
                    content=content,
                    original_message=content,
                    injected_context="",
                    alignment_score=relevance_analysis["alignment_score"],
                    cultural_relevance=relevance_analysis["cultural_relevance"]
                )
            
            # Generate context injection
            injected_content = await self._generate_context_injection(
                content, channel, strategic_context, relevance_analysis
            )
            
            # Create context injection record
            injection = ContextInjection(
                context_type=relevance_analysis["primary_context"],
                channel=channel,
                content=injected_content,
                original_message=content,
                injected_context=injected_content[len(content):],
                alignment_score=relevance_analysis["alignment_score"],
                cultural_relevance=relevance_analysis["cultural_relevance"]
            )
            
            # Store injection record
            await self._store_context_injection(injection, user_id, team_id)
            
            # Track context injection
            await self.telemetry.track_event(
                EventType.FEATURE_USED,
                user_id=user_id,
                metadata={
                    "feature": "context_injection",
                    "channel": channel.value,
                    "context_type": injection.context_type.value,
                    "alignment_score": injection.alignment_score
                }
            )
            
            logger.info(f"Context injection completed: {injection.context_type.value}")
            return injection
            
        except Exception as e:
            logger.error(f"Error injecting context: {e}")
            raise
    
    async def _get_current_strategic_context(self) -> StrategicContextData:
        """Get current strategic context from knowledge base."""
        try:
            # Get company values
            values_query = "company values cultural principles"
            values_results = await self.kb_retriever.search(values_query, limit=5)
            company_values = self._extract_values_from_results(values_results)
            
            # Get current goals
            goals_query = "current quarter goals strategic priorities"
            goals_results = await self.kb_retriever.search(goals_query, limit=5)
            current_goals = self._extract_goals_from_results(goals_results)
            
            # Get cultural principles
            culture_query = "cultural principles workplace values"
            culture_results = await self.kb_retriever.search(culture_query, limit=5)
            cultural_principles = self._extract_cultural_principles(culture_results)
            
            # Get strategic priorities
            strategy_query = "strategic priorities business objectives"
            strategy_results = await self.kb_retriever.search(strategy_query, limit=5)
            strategic_priorities = self._extract_strategic_priorities(strategy_results)
            
            # Get well-being focus
            wellbeing_query = "employee well-being workplace satisfaction"
            wellbeing_results = await self.kb_retriever.search(wellbeing_query, limit=5)
            well_being_focus = self._extract_wellbeing_focus(wellbeing_results)
            
            # Get diversity commitments
            diversity_query = "diversity inclusion commitments"
            diversity_results = await self.kb_retriever.search(diversity_query, limit=5)
            diversity_commitments = self._extract_diversity_commitments(diversity_results)
            
            return StrategicContextData(
                company_values=company_values,
                current_goals=current_goals,
                cultural_principles=cultural_principles,
                strategic_priorities=strategic_priorities,
                well_being_focus=well_being_focus,
                diversity_commitments=diversity_commitments,
                leadership_style="compassionate and values-driven",
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting strategic context: {e}")
            return self._get_default_strategic_context()
    
    async def _analyze_context_relevance(
        self,
        content: str,
        strategic_context: StrategicContextData
    ) -> Dict[str, Any]:
        """Analyze content for context relevance and alignment."""
        try:
            # Build analysis prompt
            prompt = self._build_relevance_analysis_prompt(content, strategic_context)
            
            # Get AI analysis
            response = await self.llm.agenerate([prompt])
            analysis_text = response.generations[0][0].text
            
            # Parse analysis
            analysis = self._parse_relevance_analysis(analysis_text)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing context relevance: {e}")
            return self._get_default_relevance_analysis()
    
    def _should_inject_context(
        self,
        channel: CommunicationChannel,
        relevance_analysis: Dict[str, Any]
    ) -> bool:
        """Determine if context should be injected."""
        try:
            # Get channel rules
            channel_rules = self.injection_rules.get(channel, {})
            frequency = channel_rules.get("frequency", "selective")
            
            # Check frequency rules
            if frequency == "always":
                return True
            elif frequency == "selective":
                return relevance_analysis["alignment_score"] < 0.7
            elif frequency == "task_relevant":
                return relevance_analysis["task_relevant"]
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error determining context injection: {e}")
            return False
    
    async def _generate_context_injection(
        self,
        content: str,
        channel: CommunicationChannel,
        strategic_context: StrategicContextData,
        relevance_analysis: Dict[str, Any]
    ) -> str:
        """Generate context injection for the content."""
        try:
            # Build injection prompt
            prompt = self._build_injection_prompt(
                content, channel, strategic_context, relevance_analysis
            )
            
            # Get AI-generated injection
            response = await self.llm.agenerate([prompt])
            injected_content = response.generations[0][0].text
            
            # Clean and format injection
            formatted_injection = self._format_injection(
                injected_content, channel, relevance_analysis
            )
            
            # Combine with original content
            final_content = self._combine_content(content, formatted_injection, channel)
            
            return final_content
            
        except Exception as e:
            logger.error(f"Error generating context injection: {e}")
            return content
    
    def _build_relevance_analysis_prompt(
        self,
        content: str,
        strategic_context: StrategicContextData
    ) -> str:
        """Build prompt for relevance analysis."""
        return f"""Analyze this communication content for strategic context relevance and alignment.

CONTENT: {content}

STRATEGIC CONTEXT:
- Company Values: {', '.join(strategic_context.company_values)}
- Current Goals: {json.dumps(strategic_context.current_goals)}
- Cultural Principles: {', '.join(strategic_context.cultural_principles)}
- Strategic Priorities: {', '.join(strategic_context.strategic_priorities)}
- Well-being Focus: {', '.join(strategic_context.well_being_focus)}
- Diversity Commitments: {', '.join(strategic_context.diversity_commitments)}

ANALYSIS REQUIREMENTS:
1. Alignment Score: 0.0 to 1.0 (how well content aligns with strategic context)
2. Cultural Relevance: 0.0 to 1.0 (how culturally relevant the content is)
3. Primary Context Type: values/goals/culture/strategy/well_being/diversity/leadership
4. Task Relevance: true/false (if this is task-related communication)
5. Context Gap: What strategic context is missing or could be reinforced

Provide analysis in JSON format:
{{
    "alignment_score": 0.75,
    "cultural_relevance": 0.8,
    "primary_context": "goals",
    "task_relevant": true,
    "context_gap": "Could reinforce Q4 revenue goals",
    "suggested_injection": "Remember our Q4 goal of 15% growth"
}}"""
    
    def _build_injection_prompt(
        self,
        content: str,
        channel: CommunicationChannel,
        strategic_context: StrategicContextData,
        relevance_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for context injection generation."""
        channel_rules = self.injection_rules.get(channel, {})
        style = channel_rules.get("style", "natural")
        max_length = channel_rules.get("max_length", 100)
        
        return f"""Generate a strategic context injection for this communication.

ORIGINAL CONTENT: {content}

CHANNEL: {channel.value}
STYLE: {style}
MAX LENGTH: {max_length} characters

STRATEGIC CONTEXT:
- Company Values: {', '.join(strategic_context.company_values)}
- Current Goals: {json.dumps(strategic_context.current_goals)}
- Cultural Principles: {', '.join(strategic_context.cultural_principles)}
- Strategic Priorities: {', '.join(strategic_context.strategic_priorities)}
- Well-being Focus: {', '.join(strategic_context.well_being_focus)}
- Diversity Commitments: {', '.join(strategic_context.diversity_commitments)}

CONTEXT GAP: {relevance_analysis.get('context_gap', '')}

REQUIREMENTS:
1. Natural and conversational tone
2. Relevant to the original content
3. Reinforces strategic context
4. Culturally sensitive and inclusive
5. Encourages well-being and positive culture
6. Brief and impactful

Generate only the injection text (not the full message):"""
    
    def _format_injection(
        self,
        injection: str,
        channel: CommunicationChannel,
        relevance_analysis: Dict[str, Any]
    ) -> str:
        """Format the injection based on channel and context."""
        try:
            # Clean injection text
            injection = injection.strip()
            
            # Add appropriate formatting based on channel
            if channel == CommunicationChannel.SLACK:
                return f"\n💡 *Strategic Reminder:* {injection}"
            elif channel == CommunicationChannel.EMAIL:
                return f"\n\n*Strategic Context:* {injection}"
            elif channel == CommunicationChannel.ASANA:
                return f"\n🎯 *Goal Alignment:* {injection}"
            elif channel == CommunicationChannel.MEETING:
                return f"\n📋 *Meeting Context:* {injection}"
            else:
                return f"\n{injection}"
                
        except Exception as e:
            logger.error(f"Error formatting injection: {e}")
            return injection
    
    def _combine_content(
        self,
        original: str,
        injection: str,
        channel: CommunicationChannel
    ) -> str:
        """Combine original content with injection."""
        try:
            if channel == CommunicationChannel.EMAIL:
                # For emails, add injection before signature
                if "\n\nBest regards" in original:
                    return original.replace("\n\nBest regards", f"{injection}\n\nBest regards")
                else:
                    return f"{original}{injection}"
            else:
                # For other channels, append injection
                return f"{original}{injection}"
                
        except Exception as e:
            logger.error(f"Error combining content: {e}")
            return original
    
    async def _store_context_injection(
        self,
        injection: ContextInjection,
        user_id: str,
        team_id: str = None
    ):
        """Store context injection record in database."""
        try:
            db_session = get_db_session()
            
            # Create strategic context record
            context_record = StrategicContext(
                user_id=user_id,
                team_id=team_id,
                context_type=injection.context_type.value,
                channel=injection.channel.value,
                original_content=injection.original_message,
                injected_content=injection.injected_context,
                final_content=injection.content,
                alignment_score=injection.alignment_score,
                cultural_relevance=injection.cultural_relevance,
                created_at=datetime.utcnow()
            )
            
            db_session.add(context_record)
            db_session.commit()
            db_session.close()
            
        except Exception as e:
            logger.error(f"Error storing context injection: {e}")
    
    # Helper methods for extracting context data
    def _extract_values_from_results(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract company values from search results."""
        values = []
        for result in results:
            content = result.get("content", "")
            # Simple extraction - in production, use more sophisticated NLP
            if "value" in content.lower() or "principle" in content.lower():
                values.append(content[:100])
        return values[:5] if values else ["Integrity", "Excellence", "Collaboration"]
    
    def _extract_goals_from_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract current goals from search results."""
        goals = {}
        for result in results:
            content = result.get("content", "")
            if "goal" in content.lower() or "target" in content.lower():
                goals["current_quarter"] = content[:200]
                break
        return goals if goals else {"current_quarter": "Increase revenue by 15%"}
    
    def _extract_cultural_principles(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract cultural principles from search results."""
        principles = []
        for result in results:
            content = result.get("content", "")
            if "culture" in content.lower() or "principle" in content.lower():
                principles.append(content[:100])
        return principles[:3] if principles else ["People First", "Continuous Learning", "Innovation"]
    
    def _extract_strategic_priorities(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract strategic priorities from search results."""
        priorities = []
        for result in results:
            content = result.get("content", "")
            if "priority" in content.lower() or "strategy" in content.lower():
                priorities.append(content[:100])
        return priorities[:3] if priorities else ["Customer Success", "Product Innovation", "Team Growth"]
    
    def _extract_wellbeing_focus(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract well-being focus from search results."""
        wellbeing = []
        for result in results:
            content = result.get("content", "")
            if "well" in content.lower() or "health" in content.lower():
                wellbeing.append(content[:100])
        return wellbeing[:3] if wellbeing else ["Work-Life Balance", "Mental Health", "Physical Wellness"]
    
    def _extract_diversity_commitments(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract diversity commitments from search results."""
        diversity = []
        for result in results:
            content = result.get("content", "")
            if "diversity" in content.lower() or "inclusion" in content.lower():
                diversity.append(content[:100])
        return diversity[:3] if diversity else ["Inclusive Environment", "Diverse Perspectives", "Equal Opportunity"]
    
    def _parse_relevance_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse AI relevance analysis response."""
        try:
            # Extract JSON from response
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            json_str = analysis_text[json_start:json_end]
            
            analysis = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "alignment_score", "cultural_relevance", "primary_context",
                "task_relevant", "context_gap", "suggested_injection"
            ]
            
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = self._get_default_analysis_value(field)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing relevance analysis: {e}")
            return self._get_default_relevance_analysis()
    
    def _get_default_strategic_context(self) -> StrategicContextData:
        """Get default strategic context when KB is unavailable."""
        return StrategicContextData(
            company_values=["Integrity", "Excellence", "Collaboration"],
            current_goals={"current_quarter": "Increase revenue by 15%"},
            cultural_principles=["People First", "Continuous Learning", "Innovation"],
            strategic_priorities=["Customer Success", "Product Innovation", "Team Growth"],
            well_being_focus=["Work-Life Balance", "Mental Health", "Physical Wellness"],
            diversity_commitments=["Inclusive Environment", "Diverse Perspectives", "Equal Opportunity"],
            leadership_style="compassionate and values-driven",
            last_updated=datetime.utcnow()
        )
    
    def _get_default_relevance_analysis(self) -> Dict[str, Any]:
        """Get default relevance analysis when AI fails."""
        return {
            "alignment_score": 0.5,
            "cultural_relevance": 0.5,
            "primary_context": ContextType.STRATEGY,
            "task_relevant": False,
            "context_gap": "General strategic alignment",
            "suggested_injection": "Remember our company values and goals"
        }
    
    def _get_default_analysis_value(self, field: str) -> Any:
        """Get default value for missing analysis fields."""
        defaults = {
            "alignment_score": 0.5,
            "cultural_relevance": 0.5,
            "primary_context": ContextType.STRATEGY.value,
            "task_relevant": False,
            "context_gap": "General alignment",
            "suggested_injection": "Consider our strategic priorities"
        }
        return defaults.get(field, "Unknown")


# Global instance
context_injector = StrategicContextInjector()


def get_context_injector() -> StrategicContextInjector:
    """Get the global context injector instance."""
    return context_injector


async def init_context_injector():
    """Initialize the context injector."""
    global context_injector
    context_injector = StrategicContextInjector()
    logger.info("Context injector initialized successfully")
    return context_injector 