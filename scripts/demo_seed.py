#!/usr/bin/env python3
"""Demo seeding script for Reflex AI Assistant - creates instant demo environment."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.storage.db import get_db_session
from src.storage.models import (
    User, Conversation, Message, WorkflowExecution,
    SlackChannel, SlackUser, SlackMessage,
    Email, AsanaProject, AsanaTask, AsanaStory
)
from src.kb.seeder import KnowledgeBaseSeeder

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemoSeeder:
    """Creates comprehensive demo environment with synthetic data."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db = next(get_db_session())
        self.kb_seeder = KnowledgeBaseSeeder()
        
        # Demo company data
        self.demo_company = {
            "name": "TechFlow Solutions",
            "industry": "SaaS",
            "size": "50 employees",
            "description": "AI-powered workflow automation platform"
        }
        
        # Demo users
        self.demo_users = [
            {
                "id": "U123456",
                "name": "sarah_ceo",
                "real_name": "Sarah Chen",
                "email": "sarah@techflow.com",
                "role": "CEO",
                "is_admin": True
            },
            {
                "id": "U789012",
                "name": "mike_cto",
                "real_name": "Mike Rodriguez",
                "email": "mike@techflow.com",
                "role": "CTO",
                "is_admin": True
            },
            {
                "id": "U345678",
                "name": "jen_marketing",
                "real_name": "Jennifer Park",
                "email": "jen@techflow.com",
                "role": "Marketing Director",
                "is_admin": False
            },
            {
                "id": "U901234",
                "name": "alex_sales",
                "real_name": "Alex Thompson",
                "email": "alex@techflow.com",
                "role": "Sales Manager",
                "is_admin": False
            }
        ]
        
        # Demo Slack channels
        self.demo_channels = [
            {
                "id": "C123456",
                "name": "general",
                "topic": "Company-wide announcements and discussions",
                "purpose": "Team communication and updates"
            },
            {
                "id": "C789012",
                "name": "sales",
                "topic": "Sales team coordination and updates",
                "purpose": "Sales pipeline and customer discussions"
            },
            {
                "id": "C345678",
                "name": "engineering",
                "topic": "Engineering team discussions and updates",
                "purpose": "Technical discussions and project updates"
            },
            {
                "id": "C901234",
                "name": "marketing",
                "topic": "Marketing campaigns and content",
                "purpose": "Marketing strategy and campaign coordination"
            }
        ]
        
        # Demo Slack messages
        self.demo_slack_messages = [
            {
                "channel": "general",
                "user": "sarah_ceo",
                "text": "Team, great news! We just closed our Series A funding round. Let's have a company-wide meeting tomorrow at 2 PM to discuss our growth plans.",
                "timestamp": datetime.now() - timedelta(hours=2)
            },
            {
                "channel": "general",
                "user": "mike_cto",
                "text": "Congratulations everyone! This funding will help us scale our engineering team and accelerate product development.",
                "timestamp": datetime.now() - timedelta(hours=1, minutes=45)
            },
            {
                "channel": "sales",
                "user": "alex_sales",
                "text": "We have a big opportunity with Enterprise Corp. They're looking for a solution to automate their customer support workflows. @sarah_ceo should we schedule a demo?",
                "timestamp": datetime.now() - timedelta(hours=3)
            },
            {
                "channel": "marketing",
                "user": "jen_marketing",
                "text": "New blog post is live: '5 Ways AI is Transforming Customer Support'. Please share on your social channels!",
                "timestamp": datetime.now() - timedelta(hours=4)
            },
            {
                "channel": "engineering",
                "user": "mike_cto",
                "text": "We're deploying the new voice recognition feature to production tonight. @sarah_ceo please review the release notes.",
                "timestamp": datetime.now() - timedelta(hours=5)
            }
        ]
        
        # Demo emails
        self.demo_emails = [
            {
                "from_email": "investor@venturecapital.com",
                "to_emails": "sarah@techflow.com",
                "subject": "Series A Funding - Next Steps",
                "body": "Hi Sarah, congratulations on the funding! We're excited to work with TechFlow. Let's schedule a board meeting for next week to discuss our growth strategy and milestones.",
                "labels": "INBOX,IMPORTANT",
                "received_at": datetime.now() - timedelta(hours=1)
            },
            {
                "from_email": "enterprise@enterprisecorp.com",
                "to_emails": "alex@techflow.com",
                "subject": "Product Demo Request",
                "body": "Hi Alex, we're interested in learning more about your AI workflow automation platform. Can we schedule a demo for next week? We have 500+ customer support agents that could benefit from automation.",
                "labels": "INBOX,LEADS",
                "received_at": datetime.now() - timedelta(hours=2)
            },
            {
                "from_email": "support@techflow.com",
                "to_emails": "sarah@techflow.com",
                "subject": "Customer Feedback - Feature Request",
                "body": "Hi Sarah, we received feedback from our top 10 customers requesting integration with Salesforce. This could be a significant revenue opportunity. Should we prioritize this for Q2?",
                "labels": "INBOX,FEEDBACK",
                "received_at": datetime.now() - timedelta(hours=3)
            },
            {
                "from_email": "hr@techflow.com",
                "to_emails": "sarah@techflow.com",
                "subject": "New Hire - Senior AI Engineer",
                "body": "Hi Sarah, we've made an offer to Dr. Emily Chen for the Senior AI Engineer position. She has 8 years of experience at Google and Stanford. Should we proceed with onboarding?",
                "labels": "INBOX,HR",
                "received_at": datetime.now() - timedelta(hours=4)
            }
        ]
        
        # Demo Asana projects
        self.demo_projects = [
            {
                "id": "project-123",
                "name": "Series A Growth Plan",
                "description": "Strategic initiatives to scale the company after Series A funding",
                "workspace_id": "workspace-123",
                "team_id": "team-123",
                "owner_id": "sarah_ceo",
                "color": "blue",
                "default_view": "board",
                "due_date": datetime.now() + timedelta(days=90),
                "start_on": datetime.now(),
                "is_public": True,
                "is_archived": False
            },
            {
                "id": "project-456",
                "name": "Enterprise Corp Deal",
                "description": "Sales process and implementation for Enterprise Corp",
                "workspace_id": "workspace-123",
                "team_id": "team-456",
                "owner_id": "alex_sales",
                "color": "green",
                "default_view": "list",
                "due_date": datetime.now() + timedelta(days=30),
                "start_on": datetime.now(),
                "is_public": True,
                "is_archived": False
            },
            {
                "id": "project-789",
                "name": "Voice Recognition Feature",
                "description": "Development and launch of new voice recognition capabilities",
                "workspace_id": "workspace-123",
                "team_id": "team-789",
                "owner_id": "mike_cto",
                "color": "purple",
                "default_view": "board",
                "due_date": datetime.now() + timedelta(days=14),
                "start_on": datetime.now() - timedelta(days=7),
                "is_public": True,
                "is_archived": False
            }
        ]
        
        # Demo Asana tasks
        self.demo_tasks = [
            {
                "id": "task-123",
                "name": "Hire 10 new engineers",
                "description": "Scale engineering team to support growth",
                "project_id": "project-123",
                "assignee_id": "mike_cto",
                "due_date": datetime.now() + timedelta(days=60),
                "priority": "high",
                "status": "in_progress"
            },
            {
                "id": "task-456",
                "name": "Prepare Enterprise Corp demo",
                "description": "Customize demo for Enterprise Corp's specific needs",
                "project_id": "project-456",
                "assignee_id": "alex_sales",
                "due_date": datetime.now() + timedelta(days=7),
                "priority": "high",
                "status": "not_started"
            },
            {
                "id": "task-789",
                "name": "Deploy voice recognition to production",
                "description": "Complete deployment and monitoring setup",
                "project_id": "project-789",
                "assignee_id": "mike_cto",
                "due_date": datetime.now() + timedelta(days=1),
                "priority": "high",
                "status": "in_progress"
            },
            {
                "id": "task-101",
                "name": "Create Q2 marketing campaign",
                "description": "Develop comprehensive marketing strategy for Q2",
                "project_id": "project-123",
                "assignee_id": "jen_marketing",
                "due_date": datetime.now() + timedelta(days=14),
                "priority": "medium",
                "status": "not_started"
            },
            {
                "id": "task-102",
                "name": "Board meeting preparation",
                "description": "Prepare materials for first board meeting",
                "project_id": "project-123",
                "assignee_id": "sarah_ceo",
                "due_date": datetime.now() + timedelta(days=5),
                "priority": "high",
                "status": "not_started"
            }
        ]

    async def seed_demo_environment(self):
        """Create complete demo environment."""
        logger.info("🚀 Starting demo environment setup...")
        
        try:
            # 1. Create demo users
            await self._create_demo_users()
            
            # 2. Create Slack workspace
            await self._create_slack_workspace()
            
            # 3. Create email inbox
            await self._create_email_inbox()
            
            # 4. Create Asana workspace
            await self._create_asana_workspace()
            
            # 5. Create sample conversations
            await self._create_sample_conversations()
            
            # 6. Create sample workflows
            await self._create_sample_workflows()
            
            # 7. Seed knowledge base
            await self._seed_knowledge_base()
            
            logger.info("✅ Demo environment setup complete!")
            self._print_demo_info()
            
        except Exception as e:
            logger.error(f"❌ Demo setup failed: {e}")
            raise

    async def _create_demo_users(self):
        """Create demo users in the system."""
        logger.info("👥 Creating demo users...")
        
        for user_data in self.demo_users:
            user = User(
                id=user_data["id"],
                email=user_data["email"],
                name=user_data["real_name"],
                role=user_data["role"],
                company_name=self.demo_company["name"],
                subscription_tier="professional",
                is_active=True,
                created_at=datetime.now()
            )
            self.db.add(user)
        
        self.db.commit()
        logger.info(f"✅ Created {len(self.demo_users)} demo users")

    async def _create_slack_workspace(self):
        """Create demo Slack workspace with channels and messages."""
        logger.info("💬 Creating Slack workspace...")
        
        # Create channels
        for channel_data in self.demo_channels:
            channel = SlackChannel(
                id=channel_data["id"],
                name=channel_data["name"],
                team_id="T123456",
                is_private=False,
                is_archived=False,
                member_count=len(self.demo_users),
                topic=channel_data["topic"],
                purpose=channel_data["purpose"],
                created_at=datetime.now()
            )
            self.db.add(channel)
        
        # Create users
        for user_data in self.demo_users:
            slack_user = SlackUser(
                id=user_data["id"],
                team_id="T123456",
                name=user_data["name"],
                real_name=user_data["real_name"],
                email=user_data["email"],
                is_bot=False,
                is_admin=user_data["is_admin"],
                status="active",
                created_at=datetime.now()
            )
            self.db.add(slack_user)
        
        # Create messages
        for msg_data in self.demo_slack_messages:
            # Find channel and user
            channel = self.db.query(SlackChannel).filter(
                SlackChannel.name == msg_data["channel"]
            ).first()
            
            user = self.db.query(SlackUser).filter(
                SlackUser.name == msg_data["user"]
            ).first()
            
            if channel and user:
                message = SlackMessage(
                    id=f"msg-{len(self.demo_slack_messages)}",
                    channel_id=channel.id,
                    user_id=user.id,
                    text=msg_data["text"],
                    ts=f"{int(msg_data['timestamp'].timestamp())}.000000",
                    type="message",
                    timestamp=msg_data["timestamp"]
                )
                self.db.add(message)
        
        self.db.commit()
        logger.info(f"✅ Created Slack workspace with {len(self.demo_channels)} channels and {len(self.demo_slack_messages)} messages")

    async def _create_email_inbox(self):
        """Create demo email inbox with messages."""
        logger.info("📧 Creating email inbox...")
        
        for email_data in self.demo_emails:
            email = Email(
                id=f"email-{len(self.demo_emails)}",
                thread_id=f"thread-{len(self.demo_emails)}",
                from_email=email_data["from_email"],
                to_emails=email_data["to_emails"],
                subject=email_data["subject"],
                body=email_data["body"],
                body_plain=email_data["body"],
                labels=email_data["labels"],
                is_read=False,
                is_important="IMPORTANT" in email_data["labels"],
                has_attachments=False,
                received_at=email_data["received_at"]
            )
            self.db.add(email)
        
        self.db.commit()
        logger.info(f"✅ Created email inbox with {len(self.demo_emails)} messages")

    async def _create_asana_workspace(self):
        """Create demo Asana workspace with projects and tasks."""
        logger.info("📋 Creating Asana workspace...")
        
        # Create projects
        for project_data in self.demo_projects:
            project = AsanaProject(
                id=project_data["id"],
                name=project_data["name"],
                description=project_data["description"],
                workspace_id=project_data["workspace_id"],
                team_id=project_data["team_id"],
                owner_id=project_data["owner_id"],
                color=project_data["color"],
                default_view=project_data["default_view"],
                due_date=project_data["due_date"],
                start_on=project_data["start_on"],
                is_public=project_data["is_public"],
                is_archived=project_data["is_archived"],
                created_at=datetime.now()
            )
            self.db.add(project)
        
        # Create tasks
        for task_data in self.demo_tasks:
            task = AsanaTask(
                id=task_data["id"],
                name=task_data["name"],
                description=task_data["description"],
                project_id=task_data["project_id"],
                assignee_id=task_data["assignee_id"],
                due_date=task_data["due_date"],
                is_completed=False,
                priority=task_data["priority"],
                status=task_data["status"],
                created_at=datetime.now()
            )
            self.db.add(task)
            
            # Create a story for each task
            story = AsanaStory(
                id=f"story-{task_data['id']}",
                task_id=task_data["id"],
                type="comment",
                text=f"Task created for {task_data['name']}",
                created_by_id=task_data["assignee_id"],
                resource_type="task",
                resource_subtype="comment_added",
                created_at=datetime.now()
            )
            self.db.add(story)
        
        self.db.commit()
        logger.info(f"✅ Created Asana workspace with {len(self.demo_projects)} projects and {len(self.demo_tasks)} tasks")

    async def _create_sample_conversations(self):
        """Create sample conversations with the AI assistant."""
        logger.info("💬 Creating sample conversations...")
        
        sample_conversations = [
            {
                "user_id": "U123456",  # Sarah CEO
                "platform": "slack",
                "channel_id": "C123456",
                "title": "Series A Funding Discussion",
                "messages": [
                    {
                        "content": "Help me prepare for the board meeting next week",
                        "sender": "U123456",
                        "message_type": "user"
                    },
                    {
                        "content": "I'll help you prepare for the board meeting. Based on your recent Series A funding, here are the key topics to cover:\n\n1. **Growth Strategy**: Hiring 10 engineers and expanding to new markets\n2. **Financial Projections**: Updated revenue targets and burn rate\n3. **Product Roadmap**: Voice recognition feature launch and Q2 priorities\n4. **Team Scaling**: New hires and organizational structure\n\nWould you like me to create a detailed agenda and prepare talking points for each section?",
                        "sender": "BOT_ID",
                        "message_type": "assistant"
                    }
                ]
            },
            {
                "user_id": "U789012",  # Mike CTO
                "platform": "slack",
                "channel_id": "C345678",
                "title": "Voice Recognition Deployment",
                "messages": [
                    {
                        "content": "What's the status of the voice recognition deployment?",
                        "sender": "U789012",
                        "message_type": "user"
                    },
                    {
                        "content": "The voice recognition deployment is scheduled for tonight. Here's the current status:\n\n✅ **Testing Complete**: All unit and integration tests passed\n✅ **Performance Review**: Meets latency requirements\n⚠️ **Pending**: Final security audit\n\n**Deployment Plan**:\n- 10 PM: Deploy to staging\n- 11 PM: Run smoke tests\n- 12 AM: Deploy to production\n- 1 AM: Monitor for 2 hours\n\nWould you like me to create a task for the security audit or proceed with the deployment?",
                        "sender": "BOT_ID",
                        "message_type": "assistant"
                    }
                ]
            }
        ]
        
        for conv_data in sample_conversations:
            conversation = Conversation(
                user_id=conv_data["user_id"],
                platform=conv_data["platform"],
                channel_id=conv_data["channel_id"],
                team_id="T123456",
                title=conv_data["title"],
                started_at=datetime.now() - timedelta(hours=1),
                updated_at=datetime.now()
            )
            self.db.add(conversation)
            self.db.flush()  # Get the conversation ID
            
            # Add messages
            for msg_data in conv_data["messages"]:
                message = Message(
                    conversation_id=conversation.id,
                    content=msg_data["content"],
                    sender=msg_data["sender"],
                    message_type=msg_data["message_type"],
                    timestamp=datetime.now() - timedelta(minutes=30)
                )
                self.db.add(message)
        
        self.db.commit()
        logger.info(f"✅ Created {len(sample_conversations)} sample conversations")

    async def _create_sample_workflows(self):
        """Create sample workflow executions."""
        logger.info("⚡ Creating sample workflows...")
        
        sample_workflows = [
            {
                "id": "workflow-123",
                "workflow_type": "email_triage",
                "status": "completed",
                "trigger_user": "U123456",
                "trigger_content": "Series A Funding - Next Steps",
                "result": {
                    "action": "email_triaged",
                    "priority": "high",
                    "category": "funding",
                    "suggested_response": "Thank you for the congratulations. I'll schedule the board meeting for next week."
                }
            },
            {
                "id": "workflow-456",
                "workflow_type": "task_creation",
                "status": "completed",
                "trigger_user": "U789012",
                "trigger_content": "Deploy voice recognition to production",
                "result": {
                    "action": "task_created",
                    "task_id": "task-789",
                    "assignee": "mike_cto",
                    "due_date": "2024-01-15"
                }
            },
            {
                "id": "workflow-789",
                "workflow_type": "meeting_scheduling",
                "status": "in_progress",
                "trigger_user": "U123456",
                "trigger_content": "Schedule board meeting",
                "result": {
                    "action": "meeting_scheduled",
                    "participants": ["sarah@techflow.com", "investor@venturecapital.com"],
                    "date": "2024-01-20",
                    "time": "2:00 PM"
                }
            }
        ]
        
        for workflow_data in sample_workflows:
            workflow = WorkflowExecution(
                id=workflow_data["id"],
                workflow_type=workflow_data["workflow_type"],
                status=workflow_data["status"],
                trigger_user=workflow_data["trigger_user"],
                trigger_content=workflow_data["trigger_content"],
                team_id="T123456",
                result=workflow_data["result"],
                retry_count=0,
                created_at=datetime.now() - timedelta(hours=2),
                updated_at=datetime.now() - timedelta(hours=1)
            )
            self.db.add(workflow)
        
        self.db.commit()
        logger.info(f"✅ Created {len(sample_workflows)} sample workflows")

    async def _seed_knowledge_base(self):
        """Seed the knowledge base with demo company information."""
        logger.info("🧠 Seeding knowledge base...")
        
        company_docs = [
            {
                "title": "TechFlow Solutions - Company Overview",
                "content": f"""
                TechFlow Solutions is a {self.demo_company['size']} company in the {self.demo_company['industry']} industry.
                
                **Company Description**: {self.demo_company['description']}
                
                **Leadership Team**:
                - Sarah Chen, CEO - Strategic vision and company direction
                - Mike Rodriguez, CTO - Technical leadership and product development
                - Jennifer Park, Marketing Director - Brand and growth marketing
                - Alex Thompson, Sales Manager - Revenue and customer acquisition
                
                **Recent Milestone**: Successfully closed Series A funding round
                **Growth Focus**: Scaling engineering team and expanding to new markets
                """,
                "metadata": {"type": "company_overview", "source": "demo"}
            },
            {
                "title": "TechFlow Solutions - Strategic Goals",
                "content": """
                **Q1 2024 Goals**:
                - Complete Series A funding process
                - Launch voice recognition feature
                - Hire 10 new engineers
                - Achieve $2M ARR
                
                **Q2 2024 Goals**:
                - Expand to 3 new markets
                - Launch Salesforce integration
                - Reach 100 enterprise customers
                - Achieve $5M ARR
                
                **Long-term Vision**:
                - Become the leading AI workflow automation platform
                - Serve 1000+ enterprise customers
                - Achieve $50M ARR by 2026
                """,
                "metadata": {"type": "strategic_goals", "source": "demo"}
            },
            {
                "title": "TechFlow Solutions - Products & Services",
                "content": """
                **Core Product**: AI-powered workflow automation platform
                
                **Key Features**:
                - Natural language processing for task creation
                - Voice recognition and commands
                - Integration with Slack, Gmail, Asana
                - Automated email triage and response
                - Meeting scheduling and note-taking
                - Project management automation
                
                **Target Markets**:
                - Small to medium businesses (SMB)
                - Enterprise organizations
                - Customer support teams
                - Sales and marketing teams
                
                **Pricing Tiers**:
                - Free: 50 conversations/month
                - Starter: $29/month, 500 conversations
                - Professional: $99/month, 2000 conversations
                - Enterprise: $299/month, unlimited
                """,
                "metadata": {"type": "products_services", "source": "demo"}
            }
        ]
        
        for doc in company_docs:
            await self.kb_seeder.add_document(
                title=doc["title"],
                content=doc["content"],
                metadata=doc["metadata"]
            )
        
        logger.info(f"✅ Seeded knowledge base with {len(company_docs)} documents")

    def _print_demo_info(self):
        """Print demo environment information."""
        print("\n" + "="*60)
        print("🎉 DEMO ENVIRONMENT READY!")
        print("="*60)
        print(f"🏢 Company: {self.demo_company['name']}")
        print(f"👥 Users: {len(self.demo_users)} demo users created")
        print(f"💬 Slack: {len(self.demo_channels)} channels, {len(self.demo_slack_messages)} messages")
        print(f"📧 Email: {len(self.demo_emails)} messages in inbox")
        print(f"📋 Asana: {len(self.demo_projects)} projects, {len(self.demo_tasks)} tasks")
        print(f"💬 Conversations: {len(self.demo_slack_messages)} sample conversations")
        print(f"⚡ Workflows: {len(self.demo_slack_messages)} sample workflows")
        print("\n🔑 Demo Credentials:")
        print("   CEO: sarah@techflow.com")
        print("   CTO: mike@techflow.com")
        print("   Marketing: jen@techflow.com")
        print("   Sales: alex@techflow.com")
        print("\n🚀 Ready for 5-minute demo!")
        print("="*60)


async def main():
    """Main function to run the demo seeder."""
    seeder = DemoSeeder()
    await seeder.seed_demo_environment()


if __name__ == "__main__":
    asyncio.run(main()) 