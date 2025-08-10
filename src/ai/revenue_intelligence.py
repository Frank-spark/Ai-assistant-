"""Revenue Intelligence System for Reflex Executive AI Assistant."""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI

from ..config import get_settings
from ..storage.models import RevenueOpportunity, FollowUpTask, SalesPipeline, CustomerInteraction
from ..storage.db import get_db_session
from ..analytics.telemetry import get_telemetry_service, EventType

logger = logging.getLogger(__name__)


class OpportunityType(Enum):
    """Types of revenue opportunities."""
    NEW_CUSTOMER = "new_customer"
    EXPANSION = "expansion"
    UPSELL = "upsell"
    RENEWAL = "renewal"
    REFERRAL = "referral"
    PARTNERSHIP = "partnership"
    INVESTMENT = "investment"
    ACQUISITION = "acquisition"


class OpportunityStage(Enum):
    """Stages in the revenue pipeline."""
    DISCOVERY = "discovery"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class FollowUpType(Enum):
    """Types of follow-up actions."""
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    PROPOSAL = "proposal"
    DEMO = "demo"
    CONTRACT = "contract"
    REFERRAL_REQUEST = "referral_request"
    PARTNERSHIP_DISCUSSION = "partnership_discussion"


@dataclass
class RevenueOpportunityData:
    """Revenue opportunity data structure."""
    opportunity_type: OpportunityType
    company_name: str
    contact_name: str
    contact_email: str
    estimated_value: float
    probability: float
    timeline_days: int
    description: str
    source_conversation: str
    key_indicators: List[str]
    next_steps: List[str]
    urgency_score: float


@dataclass
class FollowUpAction:
    """Follow-up action data structure."""
    follow_up_type: FollowUpType
    priority: str  # high, medium, low
    due_date: datetime
    assigned_to: str
    action_description: str
    expected_outcome: str
    revenue_impact: float
    automation_eligible: bool


class RevenueIntelligenceEngine:
    """AI-powered revenue intelligence and opportunity detection system."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.model_name,
            temperature=0.1,
            openai_api_key=self.settings.openai_api_key
        )
        self.telemetry = get_telemetry_service()
        
        # Revenue opportunity patterns
        self.opportunity_patterns = {
            OpportunityType.NEW_CUSTOMER: [
                "looking for a solution", "need help with", "interested in",
                "evaluating options", "current provider", "pain points",
                "budget available", "decision maker", "timeline"
            ],
            OpportunityType.EXPANSION: [
                "growing team", "additional licenses", "new departments",
                "scale up", "more features", "enterprise needs",
                "current usage", "success with", "want to expand"
            ],
            OpportunityType.UPSELL: [
                "premium features", "advanced capabilities", "enterprise plan",
                "current plan limitations", "need more", "upgrade",
                "better support", "additional services"
            ],
            OpportunityType.RENEWAL: [
                "contract ending", "renewal", "continue using",
                "satisfaction", "value received", "future plans",
                "concerns", "feedback"
            ],
            OpportunityType.REFERRAL: [
                "know someone", "refer", "recommend", "colleague",
                "network", "industry contact", "similar needs"
            ],
            OpportunityType.PARTNERSHIP: [
                "partnership", "collaboration", "joint venture",
                "integrate", "ecosystem", "mutual benefit",
                "strategic alliance"
            ]
        }
        
        # Follow-up automation rules
        self.follow_up_rules = {
            OpportunityType.NEW_CUSTOMER: [
                FollowUpType.DEMO,
                FollowUpType.PROPOSAL,
                FollowUpType.MEETING
            ],
            OpportunityType.EXPANSION: [
                FollowUpType.MEETING,
                FollowUpType.PROPOSAL,
                FollowUpType.CONTRACT
            ],
            OpportunityType.UPSELL: [
                FollowUpType.DEMO,
                FollowUpType.PROPOSAL,
                FollowUpType.CALL
            ],
            OpportunityType.RENEWAL: [
                FollowUpType.MEETING,
                FollowUpType.CONTRACT,
                FollowUpType.CALL
            ],
            OpportunityType.REFERRAL: [
                FollowUpType.EMAIL,
                FollowUpType.REFERRAL_REQUEST,
                FollowUpType.CALL
            ],
            OpportunityType.PARTNERSHIP: [
                FollowUpType.MEETING,
                FollowUpType.PARTNERSHIP_DISCUSSION,
                FollowUpType.PROPOSAL
            ]
        }
    
    async def analyze_conversation_for_opportunities(
        self,
        conversation_text: str,
        user_id: str,
        context: Dict[str, Any] = None
    ) -> List[RevenueOpportunityData]:
        """Analyze conversation for revenue opportunities."""
        try:
            logger.info(f"Analyzing conversation for revenue opportunities")
            
            # Detect opportunity types
            detected_opportunities = await self._detect_opportunity_types(conversation_text)
            
            # Extract opportunity details
            opportunities = []
            for opp_type in detected_opportunities:
                opportunity_data = await self._extract_opportunity_details(
                    conversation_text, opp_type, context
                )
                if opportunity_data:
                    opportunities.append(opportunity_data)
            
            # Store opportunities
            for opportunity in opportunities:
                await self._store_revenue_opportunity(opportunity, user_id)
            
            # Track analytics
            await self.telemetry.track_event(
                EventType.FEATURE_USED,
                user_id=user_id,
                metadata={
                    "feature": "revenue_intelligence",
                    "opportunities_detected": len(opportunities),
                    "opportunity_types": [opp.opportunity_type.value for opp in opportunities]
                }
            )
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error analyzing conversation for opportunities: {e}")
            return []
    
    async def generate_follow_up_actions(
        self,
        opportunity: RevenueOpportunityData,
        user_id: str
    ) -> List[FollowUpAction]:
        """Generate automated follow-up actions for revenue opportunities."""
        try:
            logger.info(f"Generating follow-up actions for {opportunity.opportunity_type.value}")
            
            # Get follow-up rules for opportunity type
            follow_up_types = self.follow_up_rules.get(opportunity.opportunity_type, [])
            
            # Generate specific actions
            follow_up_actions = []
            for follow_up_type in follow_up_types:
                action = await self._generate_follow_up_action(
                    opportunity, follow_up_type, user_id
                )
                if action:
                    follow_up_actions.append(action)
            
            # Store follow-up actions
            for action in follow_up_actions:
                await self._store_follow_up_action(action, opportunity, user_id)
            
            return follow_up_actions
            
        except Exception as e:
            logger.error(f"Error generating follow-up actions: {e}")
            return []
    
    async def track_revenue_metrics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Track revenue intelligence metrics and outcomes."""
        try:
            db_session = get_db_session()
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get opportunities
            opportunities = db_session.query(RevenueOpportunity).filter(
                RevenueOpportunity.created_at >= start_date
            ).all()
            
            # Get follow-up actions
            follow_ups = db_session.query(FollowUpTask).filter(
                FollowUpTask.created_at >= start_date
            ).all()
            
            # Get customer interactions
            interactions = db_session.query(CustomerInteraction).filter(
                CustomerInteraction.created_at >= start_date
            ).all()
            
            # Calculate metrics
            total_opportunities = len(opportunities)
            total_value = sum(opp.estimated_value for opp in opportunities)
            avg_probability = sum(opp.probability for opp in opportunities) / len(opportunities) if opportunities else 0
            
            # Pipeline stages
            pipeline_stages = {}
            for stage in OpportunityStage:
                stage_opportunities = [opp for opp in opportunities if opp.stage == stage.value]
                pipeline_stages[stage.value] = {
                    "count": len(stage_opportunities),
                    "value": sum(opp.estimated_value for opp in stage_opportunities),
                    "probability": sum(opp.probability for opp in stage_opportunities) / len(stage_opportunities) if stage_opportunities else 0
                }
            
            # Follow-up metrics
            completed_follow_ups = [f for f in follow_ups if f.completed]
            follow_up_completion_rate = len(completed_follow_ups) / len(follow_ups) if follow_ups else 0
            
            # Efficiency metrics
            avg_time_to_follow_up = self._calculate_avg_time_to_follow_up(follow_ups)
            conversion_rate = self._calculate_conversion_rate(opportunities)
            
            db_session.close()
            
            return {
                "opportunities": {
                    "total": total_opportunities,
                    "total_value": round(total_value, 2),
                    "avg_probability": round(avg_probability * 100, 1),
                    "avg_value": round(total_value / total_opportunities, 2) if total_opportunities > 0 else 0
                },
                "pipeline": pipeline_stages,
                "follow_ups": {
                    "total": len(follow_ups),
                    "completed": len(completed_follow_ups),
                    "completion_rate": round(follow_up_completion_rate * 100, 1),
                    "avg_time_to_follow_up": avg_time_to_follow_up
                },
                "efficiency": {
                    "conversion_rate": round(conversion_rate * 100, 1),
                    "opportunities_per_conversation": round(total_opportunities / len(interactions), 2) if interactions else 0,
                    "value_per_opportunity": round(total_value / total_opportunities, 2) if total_opportunities > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error tracking revenue metrics: {e}")
            return {}
    
    async def _detect_opportunity_types(self, conversation_text: str) -> List[OpportunityType]:
        """Detect opportunity types in conversation text."""
        try:
            detected_types = []
            
            # Check each opportunity type pattern
            for opp_type, patterns in self.opportunity_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in conversation_text.lower():
                        detected_types.append(opp_type)
                        break
            
            # Use AI for additional detection
            ai_detected = await self._ai_detect_opportunities(conversation_text)
            detected_types.extend(ai_detected)
            
            # Remove duplicates
            return list(set(detected_types))
            
        except Exception as e:
            logger.error(f"Error detecting opportunity types: {e}")
            return []
    
    async def _ai_detect_opportunities(self, conversation_text: str) -> List[OpportunityType]:
        """Use AI to detect additional opportunities."""
        try:
            prompt = f"""Analyze this conversation for revenue opportunities.

CONVERSATION: {conversation_text}

OPPORTUNITY TYPES:
- new_customer: Someone looking for a solution or service
- expansion: Existing customer wanting to grow usage
- upsell: Customer interested in premium features
- renewal: Contract renewal discussions
- referral: Someone offering referrals or recommendations
- partnership: Partnership or collaboration opportunities

Return only the opportunity types found as a JSON array: ["type1", "type2"]"""

            response = await self.llm.agenerate([prompt])
            result_text = response.generations[0][0].text
            
            # Parse JSON response
            try:
                detected_types = json.loads(result_text)
                return [OpportunityType(opp_type) for opp_type in detected_types if opp_type in [t.value for t in OpportunityType]]
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            logger.error(f"Error in AI opportunity detection: {e}")
            return []
    
    async def _extract_opportunity_details(
        self,
        conversation_text: str,
        opportunity_type: OpportunityType,
        context: Dict[str, Any] = None
    ) -> Optional[RevenueOpportunityData]:
        """Extract detailed opportunity information."""
        try:
            prompt = f"""Extract detailed information about this {opportunity_type.value} opportunity.

CONVERSATION: {conversation_text}

CONTEXT: {json.dumps(context) if context else '{}'}

Extract the following information in JSON format:
{{
    "company_name": "Company name if mentioned",
    "contact_name": "Contact person name",
    "contact_email": "Email address if mentioned",
    "estimated_value": 0.0,
    "probability": 0.0,
    "timeline_days": 0,
    "description": "Brief description of the opportunity",
    "key_indicators": ["indicator1", "indicator2"],
    "next_steps": ["step1", "step2"],
    "urgency_score": 0.0
}}"""

            response = await self.llm.agenerate([prompt])
            result_text = response.generations[0][0].text
            
            # Parse JSON response
            try:
                data = json.loads(result_text)
                
                return RevenueOpportunityData(
                    opportunity_type=opportunity_type,
                    company_name=data.get("company_name", "Unknown"),
                    contact_name=data.get("contact_name", "Unknown"),
                    contact_email=data.get("contact_email", ""),
                    estimated_value=float(data.get("estimated_value", 0)),
                    probability=float(data.get("probability", 0.5)),
                    timeline_days=int(data.get("timeline_days", 30)),
                    description=data.get("description", ""),
                    source_conversation=conversation_text[:500],
                    key_indicators=data.get("key_indicators", []),
                    next_steps=data.get("next_steps", []),
                    urgency_score=float(data.get("urgency_score", 0.5))
                )
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing opportunity details: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting opportunity details: {e}")
            return None
    
    async def _generate_follow_up_action(
        self,
        opportunity: RevenueOpportunityData,
        follow_up_type: FollowUpType,
        user_id: str
    ) -> Optional[FollowUpAction]:
        """Generate a specific follow-up action."""
        try:
            # Calculate due date based on urgency and type
            due_date = self._calculate_follow_up_due_date(opportunity, follow_up_type)
            
            # Determine priority
            priority = self._determine_priority(opportunity, follow_up_type)
            
            # Generate action description
            action_description = self._generate_action_description(opportunity, follow_up_type)
            
            # Calculate revenue impact
            revenue_impact = opportunity.estimated_value * opportunity.probability * 0.1  # 10% of opportunity value
            
            # Determine if automation is eligible
            automation_eligible = follow_up_type in [FollowUpType.EMAIL, FollowUpType.REFERRAL_REQUEST]
            
            return FollowUpAction(
                follow_up_type=follow_up_type,
                priority=priority,
                due_date=due_date,
                assigned_to=user_id,
                action_description=action_description,
                expected_outcome=self._get_expected_outcome(follow_up_type),
                revenue_impact=revenue_impact,
                automation_eligible=automation_eligible
            )
            
        except Exception as e:
            logger.error(f"Error generating follow-up action: {e}")
            return None
    
    def _calculate_follow_up_due_date(
        self,
        opportunity: RevenueOpportunityData,
        follow_up_type: FollowUpType
    ) -> datetime:
        """Calculate due date for follow-up action."""
        base_days = {
            FollowUpType.EMAIL: 1,
            FollowUpType.CALL: 2,
            FollowUpType.MEETING: 3,
            FollowUpType.PROPOSAL: 5,
            FollowUpType.DEMO: 2,
            FollowUpType.CONTRACT: 7,
            FollowUpType.REFERRAL_REQUEST: 1,
            FollowUpType.PARTNERSHIP_DISCUSSION: 3
        }
        
        base_delay = base_days.get(follow_up_type, 3)
        
        # Adjust based on urgency
        if opportunity.urgency_score > 0.8:
            base_delay = max(1, base_delay // 2)
        elif opportunity.urgency_score < 0.3:
            base_delay = base_delay * 2
        
        return datetime.utcnow() + timedelta(days=base_delay)
    
    def _determine_priority(
        self,
        opportunity: RevenueOpportunityData,
        follow_up_type: FollowUpType
    ) -> str:
        """Determine priority level for follow-up action."""
        # High priority factors
        high_priority_factors = [
            opportunity.urgency_score > 0.8,
            opportunity.estimated_value > 10000,
            opportunity.probability > 0.7,
            follow_up_type in [FollowUpType.CALL, FollowUpType.MEETING]
        ]
        
        # Low priority factors
        low_priority_factors = [
            opportunity.urgency_score < 0.3,
            opportunity.estimated_value < 1000,
            opportunity.probability < 0.3,
            follow_up_type == FollowUpType.EMAIL
        ]
        
        if any(high_priority_factors):
            return "high"
        elif any(low_priority_factors):
            return "low"
        else:
            return "medium"
    
    def _generate_action_description(
        self,
        opportunity: RevenueOpportunityData,
        follow_up_type: FollowUpType
    ) -> str:
        """Generate action description for follow-up."""
        descriptions = {
            FollowUpType.EMAIL: f"Send follow-up email to {opportunity.contact_name} at {opportunity.company_name}",
            FollowUpType.CALL: f"Schedule call with {opportunity.contact_name} to discuss {opportunity.opportunity_type.value}",
            FollowUpType.MEETING: f"Arrange meeting with {opportunity.contact_name} to explore {opportunity.opportunity_type.value}",
            FollowUpType.PROPOSAL: f"Prepare proposal for {opportunity.company_name} {opportunity.opportunity_type.value}",
            FollowUpType.DEMO: f"Schedule demo for {opportunity.contact_name} at {opportunity.company_name}",
            FollowUpType.CONTRACT: f"Prepare contract for {opportunity.company_name} {opportunity.opportunity_type.value}",
            FollowUpType.REFERRAL_REQUEST: f"Ask {opportunity.contact_name} for referrals in their network",
            FollowUpType.PARTNERSHIP_DISCUSSION: f"Discuss partnership opportunities with {opportunity.company_name}"
        }
        
        return descriptions.get(follow_up_type, f"Follow up on {opportunity.opportunity_type.value} with {opportunity.company_name}")
    
    def _get_expected_outcome(self, follow_up_type: FollowUpType) -> str:
        """Get expected outcome for follow-up type."""
        outcomes = {
            FollowUpType.EMAIL: "Response and next steps",
            FollowUpType.CALL: "Qualification and scheduling",
            FollowUpType.MEETING: "Requirements gathering and proposal",
            FollowUpType.PROPOSAL: "Proposal review and feedback",
            FollowUpType.DEMO: "Demo completion and next steps",
            FollowUpType.CONTRACT: "Contract review and signature",
            FollowUpType.REFERRAL_REQUEST: "Referral contacts and introductions",
            FollowUpType.PARTNERSHIP_DISCUSSION: "Partnership terms and agreement"
        }
        
        return outcomes.get(follow_up_type, "Next steps and follow-up")
    
    async def _store_revenue_opportunity(
        self,
        opportunity: RevenueOpportunityData,
        user_id: str
    ):
        """Store revenue opportunity in database."""
        try:
            db_session = get_db_session()
            
            # Create revenue opportunity record
            opp_record = RevenueOpportunity(
                user_id=user_id,
                opportunity_type=opportunity.opportunity_type.value,
                company_name=opportunity.company_name,
                contact_name=opportunity.contact_name,
                contact_email=opportunity.contact_email,
                estimated_value=opportunity.estimated_value,
                probability=opportunity.probability,
                timeline_days=opportunity.timeline_days,
                description=opportunity.description,
                source_conversation=opportunity.source_conversation,
                key_indicators=opportunity.key_indicators,
                next_steps=opportunity.next_steps,
                urgency_score=opportunity.urgency_score,
                stage=OpportunityStage.DISCOVERY.value,
                created_at=datetime.utcnow()
            )
            
            db_session.add(opp_record)
            db_session.commit()
            db_session.close()
            
        except Exception as e:
            logger.error(f"Error storing revenue opportunity: {e}")
    
    async def _store_follow_up_action(
        self,
        action: FollowUpAction,
        opportunity: RevenueOpportunityData,
        user_id: str
    ):
        """Store follow-up action in database."""
        try:
            db_session = get_db_session()
            
            # Create follow-up task record
            task_record = FollowUpTask(
                user_id=user_id,
                opportunity_id=opportunity.company_name,  # Use company name as identifier
                follow_up_type=action.follow_up_type.value,
                priority=action.priority,
                due_date=action.due_date,
                assigned_to=action.assigned_to,
                action_description=action.action_description,
                expected_outcome=action.expected_outcome,
                revenue_impact=action.revenue_impact,
                automation_eligible=action.automation_eligible,
                completed=False,
                created_at=datetime.utcnow()
            )
            
            db_session.add(task_record)
            db_session.commit()
            db_session.close()
            
        except Exception as e:
            logger.error(f"Error storing follow-up action: {e}")
    
    def _calculate_avg_time_to_follow_up(self, follow_ups: List[Any]) -> float:
        """Calculate average time to follow-up completion."""
        if not follow_ups:
            return 0.0
        
        total_days = 0
        completed_count = 0
        
        for follow_up in follow_ups:
            if follow_up.completed and follow_up.completed_at:
                days = (follow_up.completed_at - follow_up.created_at).days
                total_days += days
                completed_count += 1
        
        return total_days / completed_count if completed_count > 0 else 0.0
    
    def _calculate_conversion_rate(self, opportunities: List[Any]) -> float:
        """Calculate conversion rate from opportunities to closed won."""
        if not opportunities:
            return 0.0
        
        closed_won = len([opp for opp in opportunities if opp.stage == OpportunityStage.CLOSED_WON.value])
        return closed_won / len(opportunities)


# Global revenue intelligence instance
revenue_intelligence = RevenueIntelligenceEngine()


def get_revenue_intelligence() -> RevenueIntelligenceEngine:
    """Get the global revenue intelligence instance."""
    return revenue_intelligence 