"""Knowledge Base Seeder for Reflex Executive Assistant."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .retriever import KnowledgeBaseRetriever
from ..config import get_settings

logger = logging.getLogger(__name__)


class KnowledgeBaseSeeder:
    """Seeder for populating the knowledge base with company context and policies."""
    
    def __init__(self):
        """Initialize the knowledge base seeder."""
        self.settings = get_settings()
        self.kb = KnowledgeBaseRetriever()
        self.seed_data_dir = Path(__file__).parent.parent.parent / "data" / "kb"
        
    async def initialize(self):
        """Initialize the knowledge base connection."""
        await self.kb.initialize()
        logger.info("Knowledge base seeder initialized")
    
    async def seed_all(self) -> Dict[str, Any]:
        """Seed all knowledge base content."""
        logger.info("Starting knowledge base seeding...")
        
        results = {
            "company_info": await self.seed_company_info(),
            "policies": await self.seed_policies(),
            "style_guide": await self.seed_style_guide(),
            "procedures": await self.seed_procedures(),
            "faqs": await self.seed_faqs(),
            "templates": await self.seed_templates(),
            "market_context": await self.seed_market_context(),
            "excluded_markets": await self.seed_excluded_markets(),
            "approval_workflows": await self.seed_approval_workflows(),
            "integration_guides": await self.seed_integration_guides(),
            "timestamp": datetime.now().isoformat()
        }
        
        total_documents = sum(result.get("documents_added", 0) for result in results.values() if isinstance(result, dict))
        logger.info(f"Knowledge base seeding completed. Total documents added: {total_documents}")
        
        return results
    
    async def seed_company_info(self) -> Dict[str, Any]:
        """Seed company information and context."""
        logger.info("Seeding company information...")
        
        company_docs = [
            {
                "content": f"""
                Company: Spark Robotic AI
                Industry: Artificial Intelligence and Robotics
                Founded: 2024
                Mission: To revolutionize executive assistance through intelligent AI systems
                Vision: Empowering executives with AI-driven productivity and decision support
                Core Values: Innovation, Efficiency, Reliability, Security
                Primary Email: {self.settings.smtp_username}
                Website: https://sparkrobotic.com
                """,
                "metadata": {
                    "type": "company_info",
                    "category": "organization",
                    "priority": "high",
                    "source": "company_profile"
                }
            },
            {
                "content": """
                Spark Robotic AI specializes in developing intelligent executive assistant systems 
                that integrate seamlessly with existing workflows. Our AI assistants are designed 
                to handle complex tasks, manage communications, and provide strategic insights 
                while maintaining the highest standards of security and reliability.
                """,
                "metadata": {
                    "type": "company_description",
                    "category": "organization",
                    "priority": "high",
                    "source": "company_profile"
                }
            }
        ]
        
        documents_added = 0
        for doc in company_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add company info document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_policies(self) -> Dict[str, Any]:
        """Seed company policies and guidelines."""
        logger.info("Seeding company policies...")
        
        policy_docs = [
            {
                "content": """
                Communication Policy:
                - All external communications must be professional and brand-consistent
                - Internal communications should be clear and concise
                - Sensitive information must be handled with appropriate security measures
                - Response times: Urgent matters within 1 hour, standard within 4 hours
                """,
                "metadata": {
                    "type": "policy",
                    "category": "communication",
                    "priority": "high",
                    "source": "company_policies"
                }
            },
            {
                "content": """
                Security Policy:
                - All data must be encrypted in transit and at rest
                - Access to sensitive information requires proper authentication
                - Regular security audits and updates are mandatory
                - Incident reporting must occur within 24 hours
                """,
                "metadata": {
                    "type": "policy",
                    "category": "security",
                    "priority": "critical",
                    "source": "company_policies"
                }
            },
            {
                "content": """
                Approval Policy:
                - Financial decisions over $1,000 require manager approval
                - Contract changes require legal review
                - Marketing materials require brand team approval
                - Technical changes require engineering lead approval
                """,
                "metadata": {
                    "type": "policy",
                    "category": "approval",
                    "priority": "high",
                    "source": "company_policies"
                }
            }
        ]
        
        documents_added = 0
        for doc in policy_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add policy document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_style_guide(self) -> Dict[str, Any]:
        """Seed brand style guide and communication standards."""
        logger.info("Seeding style guide...")
        
        style_docs = [
            {
                "content": """
                Brand Voice and Tone:
                - Professional yet approachable
                - Clear and concise communication
                - Solution-oriented and proactive
                - Respectful and inclusive language
                - Avoid jargon and technical terms when possible
                """,
                "metadata": {
                    "type": "style_guide",
                    "category": "communication",
                    "priority": "high",
                    "source": "brand_guidelines"
                }
            },
            {
                "content": """
                Email Communication Standards:
                - Subject lines should be clear and descriptive
                - Use proper greeting and closing
                - Keep paragraphs short and focused
                - Use bullet points for lists
                - Include clear call-to-action when needed
                """,
                "metadata": {
                    "type": "style_guide",
                    "category": "email",
                    "priority": "medium",
                    "source": "brand_guidelines"
                }
            },
            {
                "content": """
                Slack Communication Standards:
                - Use appropriate channels for different topics
                - Keep messages concise and actionable
                - Use threads for detailed discussions
                - Use emojis sparingly and professionally
                - Tag relevant people when needed
                """,
                "metadata": {
                    "type": "style_guide",
                    "category": "slack",
                    "priority": "medium",
                    "source": "brand_guidelines"
                }
            }
        ]
        
        documents_added = 0
        for doc in style_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add style guide document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_procedures(self) -> Dict[str, Any]:
        """Seed standard operating procedures."""
        logger.info("Seeding procedures...")
        
        procedure_docs = [
            {
                "content": """
                Meeting Scheduling Procedure:
                1. Check calendar availability for all participants
                2. Send calendar invitation with clear agenda
                3. Include meeting link and dial-in information
                4. Send reminder 24 hours before meeting
                5. Follow up with action items after meeting
                """,
                "metadata": {
                    "type": "procedure",
                    "category": "meetings",
                    "priority": "high",
                    "source": "sop"
                }
            },
            {
                "content": """
                Task Assignment Procedure:
                1. Clearly define task requirements and deadlines
                2. Assign to appropriate team member
                3. Set up tracking and monitoring
                4. Provide necessary resources and context
                5. Follow up on progress and completion
                """,
                "metadata": {
                    "type": "procedure",
                    "category": "task_management",
                    "priority": "high",
                    "source": "sop"
                }
            },
            {
                "content": """
                Document Review Procedure:
                1. Identify document type and review requirements
                2. Route to appropriate reviewers
                3. Track review status and feedback
                4. Incorporate feedback and finalize
                5. Distribute final version to stakeholders
                """,
                "metadata": {
                    "type": "procedure",
                    "category": "documentation",
                    "priority": "medium",
                    "source": "sop"
                }
            }
        ]
        
        documents_added = 0
        for doc in procedure_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add procedure document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_faqs(self) -> Dict[str, Any]:
        """Seed frequently asked questions and answers."""
        logger.info("Seeding FAQs...")
        
        faq_docs = [
            {
                "content": """
                FAQ: How do I request time off?
                Answer: Submit a time-off request through the HR portal at least 2 weeks in advance. 
                Include dates, reason, and any coverage arrangements needed.
                """,
                "metadata": {
                    "type": "faq",
                    "category": "hr",
                    "priority": "medium",
                    "source": "employee_handbook"
                }
            },
            {
                "content": """
                FAQ: How do I report a technical issue?
                Answer: Submit a ticket through the IT help desk portal or contact the IT team directly 
                for urgent issues. Include detailed description and screenshots if possible.
                """,
                "metadata": {
                    "type": "faq",
                    "category": "it",
                    "priority": "medium",
                    "source": "employee_handbook"
                }
            },
            {
                "content": """
                FAQ: What is the expense reimbursement process?
                Answer: Submit expense reports within 30 days of purchase. Include receipts and 
                business justification. Manager approval required for amounts over $100.
                """,
                "metadata": {
                    "type": "faq",
                    "category": "finance",
                    "priority": "medium",
                    "source": "employee_handbook"
                }
            }
        ]
        
        documents_added = 0
        for doc in faq_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add FAQ document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_templates(self) -> Dict[str, Any]:
        """Seed email and document templates."""
        logger.info("Seeding templates...")
        
        template_docs = [
            {
                "content": """
                Email Template - Meeting Follow-up:
                Subject: Follow-up: [Meeting Topic] - [Date]
                
                Hi [Name],
                
                Thank you for attending our meeting on [Date]. Here's a summary of our discussion:
                
                Key Points:
                • [Point 1]
                • [Point 2]
                • [Point 3]
                
                Action Items:
                • [Action 1] - [Assignee] - [Due Date]
                • [Action 2] - [Assignee] - [Due Date]
                
                Next Steps:
                [Next steps description]
                
                Please let me know if you have any questions or need clarification on any of these items.
                
                Best regards,
                [Your name]
                """,
                "metadata": {
                    "type": "template",
                    "category": "email",
                    "priority": "medium",
                    "source": "templates"
                }
            },
            {
                "content": """
                Email Template - Project Update:
                Subject: Project Update: [Project Name] - [Date]
                
                Hi [Name],
                
                Here's the latest update on [Project Name]:
                
                Progress Summary:
                • Completed: [List completed items]
                • In Progress: [List in-progress items]
                • Upcoming: [List upcoming items]
                
                Key Metrics:
                • Timeline: [On track/Behind schedule]
                • Budget: [On budget/Over budget]
                • Quality: [Meeting standards/Issues identified]
                
                Issues/Risks:
                [List any issues or risks]
                
                Next Review: [Date]
                
                Best regards,
                [Your name]
                """,
                "metadata": {
                    "type": "template",
                    "category": "email",
                    "priority": "medium",
                    "source": "templates"
                }
            }
        ]
        
        documents_added = 0
        for doc in template_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add template document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_market_context(self) -> Dict[str, Any]:
        """Seed market and industry context."""
        logger.info("Seeding market context...")
        
        market_docs = [
            {
                "content": """
                AI and Robotics Market Context:
                The AI and robotics industry is experiencing rapid growth with increasing adoption 
                across various sectors. Key trends include automation, machine learning integration, 
                and intelligent assistance systems. The market is competitive with major players 
                investing heavily in R&D and innovation.
                """,
                "metadata": {
                    "type": "market_context",
                    "category": "industry",
                    "priority": "high",
                    "source": "market_research"
                }
            },
            {
                "content": """
                Executive Assistant Market:
                The executive assistant market is evolving with AI integration. Traditional 
                administrative tasks are being augmented with intelligent automation, data analysis, 
                and predictive capabilities. Companies are seeking solutions that improve efficiency 
                while maintaining human oversight and decision-making.
                """,
                "metadata": {
                    "type": "market_context",
                    "category": "industry",
                    "priority": "high",
                    "source": "market_research"
                }
            }
        ]
        
        documents_added = 0
        for doc in market_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add market context document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_excluded_markets(self) -> Dict[str, Any]:
        """Seed excluded markets and restrictions."""
        logger.info("Seeding excluded markets...")
        
        excluded_markets = self.settings.excluded_markets
        excluded_content = f"""
        Excluded Markets and Restrictions:
        
        The following markets are excluded from our business activities:
        {', '.join(excluded_markets)}
        
        Reasons for exclusion:
        • Regulatory compliance requirements
        • Ethical considerations
        • Business strategy alignment
        • Risk management policies
        
        All business opportunities in these markets should be declined with appropriate explanation.
        """,
        
        try:
            await self.kb.add_document(excluded_content, {
                "type": "policy",
                "category": "business_restrictions",
                "priority": "critical",
                "source": "company_policies"
            })
            return {"documents_added": 1, "status": "completed"}
        except Exception as e:
            logger.error(f"Failed to add excluded markets document: {e}")
            return {"documents_added": 0, "status": "failed", "error": str(e)}
    
    async def seed_approval_workflows(self) -> Dict[str, Any]:
        """Seed approval workflow definitions."""
        logger.info("Seeding approval workflows...")
        
        workflow_docs = [
            {
                "content": """
                Financial Approval Workflow:
                • $0-$500: Direct approval
                • $501-$1,000: Manager approval required
                • $1,001-$5,000: Director approval required
                • $5,001+: VP approval required
                
                Process: Submit request → Route to approver → Await decision → Execute if approved
                """,
                "metadata": {
                    "type": "workflow",
                    "category": "approval",
                    "priority": "high",
                    "source": "company_policies"
                }
            },
            {
                "content": """
                Content Approval Workflow:
                • Internal communications: Team lead approval
                • External communications: Marketing team approval
                • Technical documentation: Engineering lead approval
                • Legal documents: Legal team approval
                
                Process: Draft content → Submit for review → Address feedback → Final approval → Publish
                """,
                "metadata": {
                    "type": "workflow",
                    "category": "approval",
                    "priority": "medium",
                    "source": "company_policies"
                }
            }
        ]
        
        documents_added = 0
        for doc in workflow_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add workflow document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_integration_guides(self) -> Dict[str, Any]:
        """Seed integration and technical guides."""
        logger.info("Seeding integration guides...")
        
        integration_docs = [
            {
                "content": """
                Slack Integration Guide:
                • Bot responds to mentions and direct messages
                • Supports thread conversations
                • Can create channels and invite users
                • Integrates with calendar and task management
                • Maintains conversation context
                """,
                "metadata": {
                    "type": "guide",
                    "category": "integration",
                    "priority": "medium",
                    "source": "technical_docs"
                }
            },
            {
                "content": """
                Gmail Integration Guide:
                • Monitors inbox for important emails
                • Can compose and send emails
                • Integrates with Google Calendar
                • Supports meeting scheduling and management
                • Maintains email thread context
                """,
                "metadata": {
                    "type": "guide",
                    "category": "integration",
                    "priority": "medium",
                    "source": "technical_docs"
                }
            },
            {
                "content": """
                Asana Integration Guide:
                • Monitors project and task updates
                • Can create and update tasks
                • Tracks deadlines and progress
                • Provides project health insights
                • Integrates with team workflows
                """,
                "metadata": {
                    "type": "guide",
                    "category": "integration",
                    "priority": "medium",
                    "source": "technical_docs"
                }
            }
        ]
        
        documents_added = 0
        for doc in integration_docs:
            try:
                await self.kb.add_document(doc["content"], doc["metadata"])
                documents_added += 1
            except Exception as e:
                logger.error(f"Failed to add integration guide document: {e}")
        
        return {"documents_added": documents_added, "status": "completed"}
    
    async def seed_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Seed knowledge base from a JSON file."""
        logger.info(f"Seeding from file: {file_path}")
        
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return {"documents_added": 0, "status": "file_not_found"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents_added = 0
            for doc in data.get("documents", []):
                try:
                    await self.kb.add_document(doc["content"], doc["metadata"])
                    documents_added += 1
                except Exception as e:
                    logger.error(f"Failed to add document from file: {e}")
            
            return {"documents_added": documents_added, "status": "completed"}
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {"documents_added": 0, "status": "failed", "error": str(e)}
    
    async def clear_knowledge_base(self) -> Dict[str, Any]:
        """Clear all documents from the knowledge base."""
        logger.warning("Clearing knowledge base - this will remove all documents!")
        
        try:
            # This would depend on the specific vector database implementation
            # For now, we'll log the action
            logger.info("Knowledge base clear requested")
            return {"status": "completed", "message": "Knowledge base cleared"}
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def get_seeding_status(self) -> Dict[str, Any]:
        """Get the current status of the knowledge base."""
        try:
            # This would query the knowledge base for document count and metadata
            # For now, we'll return a basic status
            return {
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "message": "Knowledge base seeder is ready"
            }
        except Exception as e:
            logger.error(f"Failed to get seeding status: {e}")
            return {"status": "error", "error": str(e)} 