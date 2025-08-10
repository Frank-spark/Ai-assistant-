#!/usr/bin/env python3
"""Load demo data for Reflex AI Assistant showcase."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from src.storage.db import get_db_session
from src.storage.models import (
    User, Conversation, StrategicContext, Decision, 
    Meeting, CulturalMetrics, TeamAlignment, RevenueOpportunity,
    FollowUpTask, UsageLog, CompanyValues
)

logger = logging.getLogger(__name__)


class DemoDataLoader:
    """Load compelling demo data for executive showcase."""
    
    def __init__(self):
        self.db_session = get_db_session()
    
    async def load_all_demo_data(self):
        """Load all demo data."""
        try:
            logger.info("Loading Reflex AI Demo Data...")
            
            # Load users
            await self._load_users()
            
            # Load company values
            await self._load_company_values()
            
            # Load conversations
            await self._load_conversations()
            
            # Load strategic contexts
            await self._load_strategic_contexts()
            
            # Load decisions
            await self._load_decisions()
            
            # Load meetings
            await self._load_meetings()
            
            # Load cultural metrics
            await self._load_cultural_metrics()
            
            # Load team alignments
            await self._load_team_alignments()
            
            # Load revenue opportunities
            await self._load_revenue_opportunities()
            
            # Load follow-up tasks
            await self._load_follow_up_tasks()
            
            # Load usage logs
            await self._load_usage_logs()
            
            logger.info("Demo data loaded successfully!")
            
        except Exception as e:
            logger.error(f"Error loading demo data: {e}")
            raise
        finally:
            self.db_session.close()
    
    async def _load_users(self):
        """Load demo users."""
        logger.info("Loading demo users...")
        
        users_data = [
            {
                "id": "demo_executive_123",
                "email": "ceo@acme.com",
                "name": "Sarah Johnson",
                "role": "CEO",
                "subscription_tier": "Executive"
            },
            {
                "id": "demo_chro_456",
                "email": "chro@acme.com", 
                "name": "Michael Chen",
                "role": "CHRO",
                "subscription_tier": "Executive"
            },
            {
                "id": "demo_cto_789",
                "email": "cto@acme.com",
                "name": "Lisa Rodriguez",
                "role": "CTO",
                "subscription_tier": "Executive"
            }
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            self.db_session.add(user)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(users_data)} users")
    
    async def _load_company_values(self):
        """Load company values."""
        logger.info("Loading company values...")
        
        values_data = [
            {
                "value_name": "People First",
                "value_description": "We prioritize our team's well-being and growth above all else",
                "value_category": "core",
                "priority_level": 1
            },
            {
                "value_name": "Innovation",
                "value_description": "We embrace creativity and continuous improvement",
                "value_category": "core", 
                "priority_level": 2
            },
            {
                "value_name": "Integrity",
                "value_description": "We act with honesty and transparency in everything we do",
                "value_category": "core",
                "priority_level": 3
            },
            {
                "value_name": "Collaboration",
                "value_description": "We achieve more together than we could alone",
                "value_category": "cultural",
                "priority_level": 4
            },
            {
                "value_name": "Excellence",
                "value_description": "We strive for the highest quality in all our work",
                "value_category": "operational",
                "priority_level": 5
            }
        ]
        
        for value_data in values_data:
            value = CompanyValues(**value_data)
            self.db_session.add(value)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(values_data)} company values")
    
    async def _load_conversations(self):
        """Load demo conversations."""
        logger.info("Loading demo conversations...")
        
        conversations_data = [
            {
                "user_id": "demo_executive_123",
                "message": "How is our team feeling about the new remote policy?",
                "response": "Based on recent feedback: 78% of your team is positive about the change, Marketing team is most engaged, 3 teams have concerns about work-life balance. I recommend scheduling 1:1s with those teams.",
                "context": {"channel": "voice", "urgency": "normal"}
            },
            {
                "user_id": "demo_executive_123", 
                "message": "Show me our Q4 performance against goals",
                "response": "Based on your data, you're at 87% of Q4 targets. Sales team is ahead by 12%, but marketing is 8% behind. Would you like me to create an action plan?",
                "context": {"channel": "slack", "urgency": "high"}
            },
            {
                "user_id": "demo_chro_456",
                "message": "What's our current employee satisfaction score?",
                "response": "Current employee satisfaction is 87%, up 5% from last quarter. Key improvements in work-life balance and career development. Areas for focus: remote team engagement and recognition programs.",
                "context": {"channel": "email", "urgency": "normal"}
            },
            {
                "user_id": "demo_cto_789",
                "message": "Create a task for the engineering team to review the new security protocol",
                "response": "Task created: 'Review New Security Protocol' assigned to Engineering team. Due date: 2024-01-15. Priority: High. I've also scheduled a meeting for next Tuesday to discuss implementation.",
                "context": {"channel": "asana", "urgency": "high"}
            }
        ]
        
        for conv_data in conversations_data:
            conversation = Conversation(**conv_data)
            self.db_session.add(conversation)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(conversations_data)} conversations")
    
    async def _load_strategic_contexts(self):
        """Load strategic context injections."""
        logger.info("Loading strategic contexts...")
        
        contexts_data = [
            {
                "user_id": "demo_executive_123",
                "context_type": "values",
                "channel": "email",
                "original_content": "Let's review the Q4 budget",
                "injected_content": "Remember our 'People First' value when making budget decisions",
                "final_content": "Let's review the Q4 budget\n\n*Strategic Context:* Remember our 'People First' value when making budget decisions",
                "alignment_score": 0.85,
                "cultural_relevance": 0.9
            },
            {
                "user_id": "demo_chro_456",
                "context_type": "goals",
                "channel": "slack",
                "original_content": "Team meeting tomorrow at 2pm",
                "injected_content": "*Strategic Reminder:* Focus on our Q4 goal of 15% employee satisfaction improvement",
                "final_content": "Team meeting tomorrow at 2pm\n*Strategic Reminder:* Focus on our Q4 goal of 15% employee satisfaction improvement",
                "alignment_score": 0.92,
                "cultural_relevance": 0.88
            }
        ]
        
        for context_data in contexts_data:
            context = StrategicContext(**context_data)
            self.db_session.add(context)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(contexts_data)} strategic contexts")
    
    async def _load_decisions(self):
        """Load demo decisions."""
        logger.info("Loading demo decisions...")
        
        decisions_data = [
            {
                "decision_type": "budget_approval",
                "title": "Marketing Budget Increase",
                "description": "Additional budget for Q4 campaigns to meet growth targets",
                "amount": 50000,
                "requester": "marketing_director",
                "recommendation": "APPROVE",
                "confidence_score": 0.92,
                "reasoning": "Strong ROI projection, aligns with Q4 goals, team has proven track record",
                "risk_assessment": "Low",
                "business_impact": {"revenue_impact": 150000, "timeline": "Q4 2024"},
                "compliance_check": {"status": "compliant", "notes": "Within budget guidelines"},
                "auto_approval_eligible": True,
                "required_approvals": ["ceo"],
                "status": "approved",
                "approved_by": "demo_executive_123"
            },
            {
                "decision_type": "hiring",
                "title": "Senior Engineer Hire",
                "description": "Hire senior engineer for new product development",
                "amount": 120000,
                "requester": "engineering_manager",
                "recommendation": "APPROVE",
                "confidence_score": 0.88,
                "reasoning": "Critical for product roadmap, candidate is excellent cultural fit",
                "risk_assessment": "Medium",
                "business_impact": {"product_impact": "high", "timeline": "Q1 2025"},
                "compliance_check": {"status": "compliant", "notes": "Within hiring budget"},
                "auto_approval_eligible": False,
                "required_approvals": ["cto", "ceo"],
                "status": "pending"
            }
        ]
        
        for decision_data in decisions_data:
            decision = Decision(**decision_data)
            self.db_session.add(decision)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(decisions_data)} decisions")
    
    async def _load_meetings(self):
        """Load demo meetings."""
        logger.info("Loading demo meetings...")
        
        meetings_data = [
            {
                "title": "Q4 Strategy Review",
                "meeting_type": "strategy",
                "status": "scheduled",
                "start_time": datetime.utcnow() + timedelta(days=1),
                "end_time": datetime.utcnow() + timedelta(days=1, hours=1),
                "participants": ["demo_executive_123", "demo_chro_456", "demo_cto_789"]
            },
            {
                "title": "Team Culture Workshop",
                "meeting_type": "culture",
                "status": "scheduled", 
                "start_time": datetime.utcnow() + timedelta(days=3),
                "end_time": datetime.utcnow() + timedelta(days=3, hours=2),
                "participants": ["demo_chro_456", "hr_team"]
            }
        ]
        
        for meeting_data in meetings_data:
            meeting = Meeting(**meeting_data)
            self.db_session.add(meeting)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(meetings_data)} meetings")
    
    async def _load_cultural_metrics(self):
        """Load cultural metrics."""
        logger.info("Loading cultural metrics...")
        
        metrics_data = [
            {
                "metric_name": "Employee Satisfaction",
                "metric_value": 87.3,
                "metric_category": "satisfaction",
                "period_start": datetime.utcnow() - timedelta(days=30),
                "period_end": datetime.utcnow(),
                "source": "survey",
                "trend": "improving"
            },
            {
                "metric_name": "Team Engagement",
                "metric_value": 78.5,
                "metric_category": "engagement",
                "period_start": datetime.utcnow() - timedelta(days=30),
                "period_end": datetime.utcnow(),
                "source": "system",
                "trend": "improving"
            },
            {
                "metric_name": "Work-Life Balance",
                "metric_value": 82.1,
                "metric_category": "well_being",
                "period_start": datetime.utcnow() - timedelta(days=30),
                "period_end": datetime.utcnow(),
                "source": "survey",
                "trend": "stable"
            }
        ]
        
        for metric_data in metrics_data:
            metric = CulturalMetrics(**metric_data)
            self.db_session.add(metric)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(metrics_data)} cultural metrics")
    
    async def _load_team_alignments(self):
        """Load team alignments."""
        logger.info("Loading team alignments...")
        
        alignments_data = [
            {
                "team_id": "marketing_team",
                "team_name": "Marketing",
                "goal_id": "q4_growth",
                "goal_name": "Q4 Revenue Growth",
                "alignment_score": 0.92,
                "progress_percentage": 87.0,
                "last_assessment": datetime.utcnow() - timedelta(days=7),
                "next_assessment": datetime.utcnow() + timedelta(days=7)
            },
            {
                "team_id": "engineering_team",
                "team_name": "Engineering",
                "goal_id": "product_launch",
                "goal_name": "Product Launch",
                "alignment_score": 0.88,
                "progress_percentage": 75.0,
                "last_assessment": datetime.utcnow() - timedelta(days=5),
                "next_assessment": datetime.utcnow() + timedelta(days=9)
            }
        ]
        
        for alignment_data in alignments_data:
            alignment = TeamAlignment(**alignment_data)
            self.db_session.add(alignment)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(alignments_data)} team alignments")
    
    async def _load_revenue_opportunities(self):
        """Load revenue opportunities."""
        logger.info("Loading revenue opportunities...")
        
        opportunities_data = [
            {
                "user_id": "demo_executive_123",
                "opportunity_type": "new_customer",
                "company_name": "TechCorp Solutions",
                "contact_name": "Jennifer Smith",
                "contact_email": "jennifer@techcorp.com",
                "estimated_value": 75000,
                "probability": 0.75,
                "timeline_days": 45,
                "description": "Enterprise software licensing opportunity",
                "source_conversation": "Discussed their scaling needs and current pain points",
                "key_indicators": ["budget approved", "decision maker", "timeline urgent"],
                "next_steps": ["Schedule demo", "Prepare proposal", "Follow up"],
                "urgency_score": 0.8,
                "stage": "qualification",
                "status": "active"
            },
            {
                "user_id": "demo_executive_123",
                "opportunity_type": "expansion",
                "company_name": "Growth Inc",
                "contact_name": "David Chen",
                "contact_email": "david@growthinc.com",
                "estimated_value": 45000,
                "probability": 0.85,
                "timeline_days": 30,
                "description": "Additional licenses for growing team",
                "source_conversation": "Team expanding from 50 to 75 employees",
                "key_indicators": ["existing customer", "successful implementation", "budget available"],
                "next_steps": ["Review current usage", "Prepare expansion proposal"],
                "urgency_score": 0.6,
                "stage": "proposal",
                "status": "active"
            }
        ]
        
        for opp_data in opportunities_data:
            opportunity = RevenueOpportunity(**opp_data)
            self.db_session.add(opportunity)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(opportunities_data)} revenue opportunities")
    
    async def _load_follow_up_tasks(self):
        """Load follow-up tasks."""
        logger.info("Loading follow-up tasks...")
        
        tasks_data = [
            {
                "user_id": "demo_executive_123",
                "opportunity_id": "TechCorp Solutions",
                "follow_up_type": "demo",
                "priority": "high",
                "due_date": datetime.utcnow() + timedelta(days=2),
                "assigned_to": "demo_executive_123",
                "action_description": "Schedule demo for TechCorp Solutions",
                "expected_outcome": "Demo completion and next steps",
                "revenue_impact": 5625,
                "automation_eligible": False,
                "completed": False
            },
            {
                "user_id": "demo_executive_123",
                "opportunity_id": "Growth Inc",
                "follow_up_type": "proposal",
                "priority": "medium",
                "due_date": datetime.utcnow() + timedelta(days=5),
                "assigned_to": "demo_executive_123",
                "action_description": "Prepare expansion proposal for Growth Inc",
                "expected_outcome": "Proposal review and feedback",
                "revenue_impact": 3825,
                "automation_eligible": True,
                "completed": False
            }
        ]
        
        for task_data in tasks_data:
            task = FollowUpTask(**task_data)
            self.db_session.add(task)
        
        self.db_session.commit()
        logger.info(f"Loaded {len(tasks_data)} follow-up tasks")
    
    async def _load_usage_logs(self):
        """Load usage logs."""
        logger.info("Loading usage logs...")
        
        # Generate usage logs for the past 30 days
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            
            # Generate multiple events per day
            for j in range(5):
                event_time = date + timedelta(hours=j*4)
                
                usage_log = UsageLog(
                    user_id="demo_executive_123",
                    event_type="conversation_started",
                    metadata={"channel": "voice", "duration": 120},
                    timestamp=event_time,
                    success=True
                )
                self.db_session.add(usage_log)
        
        self.db_session.commit()
        logger.info("Loaded usage logs")


async def main():
    """Main function to load demo data."""
    loader = DemoDataLoader()
    await loader.load_all_demo_data()


if __name__ == "__main__":
    asyncio.run(main()) 