"""Executive Decision Intelligence Engine for Reflex AI Assistant."""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import uuid

from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import ChatOpenAI

from ..config import get_settings
from ..storage.models import Decision, DecisionContext, BusinessMetrics
from ..storage.db import get_db_session
from ..kb.enhanced_retriever import get_enhanced_kb_retriever
from ..analytics.telemetry import get_telemetry_service, EventType

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions that can be made."""
    APPROVAL = "approval"
    INVESTMENT = "investment"
    HIRING = "hiring"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"
    RISK = "risk"


class DecisionPriority(Enum):
    """Decision priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionStatus(Enum):
    """Decision status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class DecisionRequest:
    """Request for a decision."""
    decision_id: str
    decision_type: DecisionType
    title: str
    description: str
    amount: Optional[float] = None
    impact_areas: List[str] = None
    urgency: DecisionPriority = DecisionPriority.MEDIUM
    requester: str = ""
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.impact_areas is None:
            self.impact_areas = []
        if self.context is None:
            self.context = {}


@dataclass
class DecisionAnalysis:
    """Analysis of a decision request."""
    decision_id: str
    recommendation: str  # APPROVE, REJECT, REVIEW
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    risk_assessment: str
    business_impact: Dict[str, Any]
    compliance_check: Dict[str, Any]
    auto_approval_eligible: bool
    required_approvals: List[str]
    timeline_impact: str
    cost_benefit_analysis: Dict[str, Any]


class ExecutiveDecisionEngine:
    """AI-powered decision intelligence engine for executives."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.model_name,
            temperature=0.1,
            openai_api_key=self.settings.openai_api_key
        )
        self.kb_retriever = get_enhanced_kb_retriever()
        self.telemetry = get_telemetry_service()
        
        # Decision thresholds and rules
        self.auto_approval_thresholds = {
            DecisionType.OPERATIONAL: 0.8,
            DecisionType.APPROVAL: 0.85,
            DecisionType.INVESTMENT: 0.9,
            DecisionType.STRATEGIC: 0.95,
            DecisionType.HIRING: 0.9,
            DecisionType.COMPLIANCE: 0.95,
            DecisionType.RISK: 0.9
        }
        
        # Amount thresholds for auto-approval
        self.amount_thresholds = {
            DecisionType.APPROVAL: 5000,  # $5K
            DecisionType.INVESTMENT: 10000,  # $10K
            DecisionType.OPERATIONAL: 2000,  # $2K
        }
        
        logger.info("Executive Decision Engine initialized")
    
    async def analyze_decision(self, request: DecisionRequest) -> DecisionAnalysis:
        """Analyze a decision request and provide intelligence."""
        try:
            logger.info(f"Analyzing decision: {request.title}")
            
            # Track decision analysis
            await self.telemetry.track_event(
                EventType.FEATURE_USED,
                metadata={
                    "feature": "decision_analysis",
                    "decision_type": request.decision_type.value,
                    "amount": request.amount
                }
            )
            
            # Gather business context
            business_context = await self._gather_business_context(request)
            
            # Analyze decision with AI
            analysis_result = await self._ai_decision_analysis(request, business_context)
            
            # Determine auto-approval eligibility
            auto_approval_eligible = self._check_auto_approval_eligibility(
                request, analysis_result
            )
            
            # Create decision analysis
            analysis = DecisionAnalysis(
                decision_id=request.decision_id,
                recommendation=analysis_result["recommendation"],
                confidence_score=analysis_result["confidence_score"],
                reasoning=analysis_result["reasoning"],
                risk_assessment=analysis_result["risk_assessment"],
                business_impact=analysis_result["business_impact"],
                compliance_check=analysis_result["compliance_check"],
                auto_approval_eligible=auto_approval_eligible,
                required_approvals=analysis_result["required_approvals"],
                timeline_impact=analysis_result["timeline_impact"],
                cost_benefit_analysis=analysis_result["cost_benefit_analysis"]
            )
            
            # Store decision in database
            await self._store_decision(request, analysis)
            
            logger.info(f"Decision analysis completed: {analysis.recommendation}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing decision: {e}")
            raise
    
    async def _gather_business_context(self, request: DecisionRequest) -> Dict[str, Any]:
        """Gather relevant business context for decision making."""
        try:
            context = {
                "current_performance": await self._get_current_performance(),
                "strategic_goals": await self._get_strategic_goals(),
                "budget_status": await self._get_budget_status(),
                "risk_profile": await self._get_risk_profile(),
                "compliance_requirements": await self._get_compliance_requirements(),
                "market_conditions": await self._get_market_conditions(),
                "team_capacity": await self._get_team_capacity(),
                "historical_decisions": await self._get_similar_decisions(request)
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error gathering business context: {e}")
            return {}
    
    async def _ai_decision_analysis(self, request: DecisionRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to analyze the decision."""
        try:
            # Build analysis prompt
            prompt = self._build_decision_prompt(request, context)
            
            # Get AI response
            response = await self.llm.agenerate([prompt])
            ai_response = response.generations[0][0].text
            
            # Parse AI response
            analysis = self._parse_ai_decision_response(ai_response)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in AI decision analysis: {e}")
            return self._get_fallback_analysis(request)
    
    def _build_decision_prompt(self, request: DecisionRequest, context: Dict[str, Any]) -> str:
        """Build the prompt for AI decision analysis."""
        return f"""You are an executive decision intelligence system. Analyze this decision request and provide a comprehensive recommendation.

DECISION REQUEST:
- Type: {request.decision_type.value}
- Title: {request.title}
- Description: {request.description}
- Amount: ${request.amount if request.amount else 'N/A'}
- Urgency: {request.urgency.value}
- Impact Areas: {', '.join(request.impact_areas)}

BUSINESS CONTEXT:
{json.dumps(context, indent=2)}

ANALYSIS REQUIREMENTS:
1. Recommendation: APPROVE, REJECT, or REVIEW
2. Confidence Score: 0.0 to 1.0
3. Detailed reasoning
4. Risk assessment (Low/Medium/High)
5. Business impact analysis
6. Compliance check
7. Required approvals
8. Timeline impact
9. Cost-benefit analysis

Provide your analysis in JSON format:
{{
    "recommendation": "APPROVE/REJECT/REVIEW",
    "confidence_score": 0.85,
    "reasoning": "Detailed explanation...",
    "risk_assessment": "Low/Medium/High",
    "business_impact": {{
        "revenue_impact": "Positive/Negative/Neutral",
        "efficiency_impact": "Improves/Reduces/No change",
        "strategic_alignment": "High/Medium/Low"
    }},
    "compliance_check": {{
        "status": "Compliant/Non-compliant/Review required",
        "issues": ["List any compliance issues"]
    }},
    "required_approvals": ["List of required approvers"],
    "timeline_impact": "Immediate/Short-term/Long-term",
    "cost_benefit_analysis": {{
        "roi_projection": "2.5x",
        "payback_period": "6 months",
        "risk_adjusted_return": "15%"
    }}
}}"""
    
    def _parse_ai_decision_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            analysis = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "recommendation", "confidence_score", "reasoning",
                "risk_assessment", "business_impact", "compliance_check",
                "required_approvals", "timeline_impact", "cost_benefit_analysis"
            ]
            
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = self._get_default_value(field)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._get_fallback_analysis()
    
    def _check_auto_approval_eligibility(self, request: DecisionRequest, analysis: Dict[str, Any]) -> bool:
        """Check if decision can be auto-approved."""
        try:
            # Check confidence threshold
            confidence_threshold = self.auto_approval_thresholds.get(
                request.decision_type, 0.9
            )
            
            if analysis["confidence_score"] < confidence_threshold:
                return False
            
            # Check amount threshold
            if request.amount:
                amount_threshold = self.amount_thresholds.get(
                    request.decision_type, 0
                )
                if request.amount > amount_threshold:
                    return False
            
            # Check risk level
            if analysis["risk_assessment"].lower() == "high":
                return False
            
            # Check compliance
            if analysis["compliance_check"]["status"] != "Compliant":
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking auto-approval eligibility: {e}")
            return False
    
    async def _store_decision(self, request: DecisionRequest, analysis: DecisionAnalysis):
        """Store decision in database."""
        try:
            db_session = get_db_session()
            
            # Create decision record
            decision = Decision(
                id=request.decision_id,
                decision_type=request.decision_type.value,
                title=request.title,
                description=request.description,
                amount=request.amount,
                requester=request.requester,
                recommendation=analysis.recommendation,
                confidence_score=analysis.confidence_score,
                reasoning=analysis.reasoning,
                risk_assessment=analysis.risk_assessment,
                business_impact=analysis.business_impact,
                compliance_check=analysis.compliance_check,
                auto_approval_eligible=analysis.auto_approval_eligible,
                required_approvals=analysis.required_approvals,
                status=DecisionStatus.PENDING.value,
                created_at=datetime.utcnow()
            )
            
            db_session.add(decision)
            db_session.commit()
            db_session.close()
            
        except Exception as e:
            logger.error(f"Error storing decision: {e}")
    
    async def get_decision_summary(self, decision_id: str) -> Dict[str, Any]:
        """Get summary of a decision."""
        try:
            db_session = get_db_session()
            
            decision = db_session.query(Decision).filter(
                Decision.id == decision_id
            ).first()
            
            if not decision:
                raise ValueError(f"Decision {decision_id} not found")
            
            db_session.close()
            
            return {
                "id": decision.id,
                "title": decision.title,
                "recommendation": decision.recommendation,
                "confidence_score": decision.confidence_score,
                "status": decision.status,
                "auto_approval_eligible": decision.auto_approval_eligible,
                "created_at": decision.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting decision summary: {e}")
            raise
    
    async def approve_decision(self, decision_id: str, approver: str, notes: str = "") -> bool:
        """Approve a decision."""
        try:
            db_session = get_db_session()
            
            decision = db_session.query(Decision).filter(
                Decision.id == decision_id
            ).first()
            
            if not decision:
                raise ValueError(f"Decision {decision_id} not found")
            
            decision.status = DecisionStatus.APPROVED.value
            decision.approved_by = approver
            decision.approved_at = datetime.utcnow()
            decision.approval_notes = notes
            
            db_session.commit()
            db_session.close()
            
            # Track approval
            await self.telemetry.track_event(
                EventType.FEATURE_USED,
                metadata={
                    "feature": "decision_approval",
                    "decision_id": decision_id,
                    "approver": approver
                }
            )
            
            logger.info(f"Decision {decision_id} approved by {approver}")
            return True
            
        except Exception as e:
            logger.error(f"Error approving decision: {e}")
            return False
    
    # Helper methods for gathering business context
    async def _get_current_performance(self) -> Dict[str, Any]:
        """Get current business performance metrics."""
        # TODO: Implement actual metrics gathering
        return {
            "revenue_growth": "12%",
            "profit_margin": "18%",
            "customer_satisfaction": "4.2/5",
            "employee_retention": "92%"
        }
    
    async def _get_strategic_goals(self) -> Dict[str, Any]:
        """Get current strategic goals."""
        # TODO: Implement actual goals retrieval
        return {
            "q4_revenue_target": "$2.5M",
            "customer_acquisition": "500 new customers",
            "product_launch": "Q1 2024",
            "market_expansion": "3 new markets"
        }
    
    async def _get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        # TODO: Implement actual budget tracking
        return {
            "total_budget": "$1M",
            "spent": "$650K",
            "remaining": "$350K",
            "utilization": "65%"
        }
    
    async def _get_risk_profile(self) -> Dict[str, Any]:
        """Get current risk profile."""
        # TODO: Implement actual risk assessment
        return {
            "overall_risk": "Medium",
            "financial_risk": "Low",
            "operational_risk": "Medium",
            "compliance_risk": "Low"
        }
    
    async def _get_compliance_requirements(self) -> List[str]:
        """Get current compliance requirements."""
        # TODO: Implement actual compliance tracking
        return [
            "SOC 2 compliance",
            "GDPR compliance",
            "Industry regulations"
        ]
    
    async def _get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions."""
        # TODO: Implement actual market analysis
        return {
            "market_growth": "8%",
            "competition_level": "High",
            "economic_outlook": "Stable"
        }
    
    async def _get_team_capacity(self) -> Dict[str, Any]:
        """Get current team capacity."""
        # TODO: Implement actual capacity tracking
        return {
            "available_capacity": "75%",
            "critical_roles": ["Engineering", "Sales"],
            "hiring_needs": ["Marketing Manager"]
        }
    
    async def _get_similar_decisions(self, request: DecisionRequest) -> List[Dict[str, Any]]:
        """Get similar historical decisions."""
        # TODO: Implement actual decision history
        return [
            {
                "title": "Marketing Campaign Approval",
                "amount": 15000,
                "outcome": "Successful",
                "roi": "2.8x"
            }
        ]
    
    def _get_fallback_analysis(self, request: Optional[DecisionRequest] = None) -> Dict[str, Any]:
        """Get fallback analysis when AI fails."""
        return {
            "recommendation": "REVIEW",
            "confidence_score": 0.5,
            "reasoning": "Unable to complete full analysis - manual review recommended",
            "risk_assessment": "Medium",
            "business_impact": {
                "revenue_impact": "Unknown",
                "efficiency_impact": "Unknown",
                "strategic_alignment": "Unknown"
            },
            "compliance_check": {
                "status": "Review required",
                "issues": ["Analysis incomplete"]
            },
            "required_approvals": ["Executive review"],
            "timeline_impact": "Unknown",
            "cost_benefit_analysis": {
                "roi_projection": "Unknown",
                "payback_period": "Unknown",
                "risk_adjusted_return": "Unknown"
            }
        }
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields."""
        defaults = {
            "recommendation": "REVIEW",
            "confidence_score": 0.5,
            "reasoning": "Analysis incomplete",
            "risk_assessment": "Medium",
            "business_impact": {},
            "compliance_check": {"status": "Review required", "issues": []},
            "required_approvals": [],
            "timeline_impact": "Unknown",
            "cost_benefit_analysis": {}
        }
        return defaults.get(field, "Unknown")


# Global instance
decision_engine = ExecutiveDecisionEngine()


def get_decision_engine() -> ExecutiveDecisionEngine:
    """Get the global decision engine instance."""
    return decision_engine


async def init_decision_engine():
    """Initialize the decision engine."""
    global decision_engine
    decision_engine = ExecutiveDecisionEngine()
    logger.info("Decision engine initialized successfully")
    return decision_engine 