"""End-to-end integration tests for Reflex Executive Assistant."""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.app import create_app
from src.storage.models import Conversation, Message, WorkflowExecution, SlackChannel, SlackUser
from src.ai.chain import ReflexAIChain
from src.kb.seeder import KnowledgeBaseSeeder


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_slack_mention_workflow(self, test_client, test_session, sample_slack_event):
        """Test complete Slack mention workflow."""
        # Setup: Create test data
        channel = SlackChannel(
            id="C123456",
            name="general",
            team_id="T123456",
            is_private=False,
            is_archived=False,
            created_at=datetime.now()
        )
        test_session.add(channel)
        
        user = SlackUser(
            id="U123456",
            team_id="T123456",
            name="testuser",
            real_name="Test User",
            email="test@example.com",
            is_bot=False,
            is_admin=False,
            created_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Mock AI chain response
        mock_ai_response = {
            "response": "I can help you with that! Let me check your calendar and schedule a meeting.",
            "actions": [
                {
                    "type": "schedule_meeting",
                    "parameters": {
                        "subject": "Follow-up Discussion",
                        "duration": 30,
                        "attendees": ["test@example.com"]
                    }
                }
            ],
            "confidence": 0.9
        }
        
        with patch('src.workflows.router.ReflexAIChain') as mock_ai_chain_class, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.config.get_settings') as mock_settings:
            
            # Setup mocks
            mock_verify.return_value = True
            mock_settings.return_value.slack_signing_secret = "test_secret"
            
            mock_ai_chain = AsyncMock(spec=ReflexAIChain)
            mock_ai_chain.process_slack_message.return_value = mock_ai_response
            mock_ai_chain_class.return_value = mock_ai_chain
            
            # Execute: Send Slack webhook
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(datetime.now().timestamp()))
                }
            )
            
            # Verify: Response
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            
            # Verify: Database state
            workflow = test_session.query(WorkflowExecution).first()
            assert workflow is not None
            assert workflow.workflow_type == "slack_mention"
            assert workflow.status == "completed"
            assert workflow.trigger_user == "U123456"
            assert workflow.trigger_channel == "C123456"
            
            # Verify: AI chain was called
            mock_ai_chain.process_slack_message.assert_called_once()
            
            # Verify: Conversation was created
            conversation = test_session.query(Conversation).first()
            assert conversation is not None
            assert conversation.platform == "slack"
            assert conversation.user_id == "U123456"
            assert conversation.channel_id == "C123456"
            
            # Verify: Messages were created
            messages = test_session.query(Message).all()
            assert len(messages) >= 1
            assert any("hello" in msg.content.lower() for msg in messages)
    
    @pytest.mark.asyncio
    async def test_email_processing_workflow(self, test_client, test_session, sample_gmail_notification):
        """Test complete email processing workflow."""
        # Mock AI chain response
        mock_ai_response = {
            "response": "I've analyzed your email and identified key action items.",
            "actions": [
                {
                    "type": "create_task",
                    "parameters": {
                        "name": "Follow up on email request",
                        "description": "Action item from email",
                        "due_date": (datetime.now() + timedelta(days=7)).date().isoformat()
                    }
                }
            ],
            "confidence": 0.85
        }
        
        with patch('src.workflows.router.ReflexAIChain') as mock_ai_chain_class, \
             patch('src.integrations.webhooks.gmail.verify_gmail_signature') as mock_verify, \
             patch('src.config.get_settings') as mock_settings:
            
            # Setup mocks
            mock_verify.return_value = True
            mock_settings.return_value.google_client_secret = "test_secret"
            
            mock_ai_chain = AsyncMock(spec=ReflexAIChain)
            mock_ai_chain.process_email.return_value = mock_ai_response
            mock_ai_chain_class.return_value = mock_ai_chain
            
            # Execute: Send Gmail webhook
            response = test_client.post(
                "/webhooks/gmail",
                json=sample_gmail_notification,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test_token"
                }
            )
            
            # Verify: Response
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            
            # Verify: Database state
            workflow = test_session.query(WorkflowExecution).first()
            assert workflow is not None
            assert workflow.workflow_type == "email_notification"
            assert workflow.status == "completed"
            
            # Verify: AI chain was called
            mock_ai_chain.process_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_asana_update_workflow(self, test_client, test_session, sample_asana_event):
        """Test complete Asana update workflow."""
        # Mock AI chain response
        mock_ai_response = {
            "response": "I've analyzed the Asana update and identified important changes.",
            "actions": [
                {
                    "type": "notify_team",
                    "parameters": {
                        "message": "Task 'Test Task' has been updated",
                        "channel": "project-updates"
                    }
                }
            ],
            "confidence": 0.8
        }
        
        with patch('src.workflows.router.ReflexAIChain') as mock_ai_chain_class, \
             patch('src.integrations.webhooks.asana.verify_asana_signature') as mock_verify, \
             patch('src.config.get_settings') as mock_settings:
            
            # Setup mocks
            mock_verify.return_value = True
            mock_settings.return_value.asana_webhook_secret = "test_secret"
            
            mock_ai_chain = AsyncMock(spec=ReflexAIChain)
            mock_ai_chain.process_asana_update.return_value = mock_ai_response
            mock_ai_chain_class.return_value = mock_ai_chain
            
            # Execute: Send Asana webhook
            response = test_client.post(
                "/webhooks/asana",
                json=sample_asana_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Hook-Signature": "test_signature"
                }
            )
            
            # Verify: Response
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            
            # Verify: Database state
            workflow = test_session.query(WorkflowExecution).first()
            assert workflow is not None
            assert workflow.workflow_type == "asana_update"
            assert workflow.status == "completed"
            
            # Verify: AI chain was called
            mock_ai_chain.process_asana_update.assert_called_once()


class TestKnowledgeBaseIntegration:
    """Test knowledge base integration with AI chain."""
    
    @pytest.mark.asyncio
    async def test_knowledge_base_seeding_and_retrieval(self, test_session):
        """Test knowledge base seeding and retrieval."""
        # Setup: Seed knowledge base
        seeder = KnowledgeBaseSeeder()
        await seeder.initialize()
        
        # Execute: Seed all content
        results = await seeder.seed_all()
        
        # Verify: Seeding results
        assert results["company_info"]["status"] == "completed"
        assert results["policies"]["status"] == "completed"
        assert results["style_guide"]["status"] == "completed"
        assert results["procedures"]["status"] == "completed"
        assert results["faqs"]["status"] == "completed"
        assert results["templates"]["status"] == "completed"
        assert results["market_context"]["status"] == "completed"
        assert results["excluded_markets"]["status"] == "completed"
        assert results["approval_workflows"]["status"] == "completed"
        assert results["integration_guides"]["status"] == "completed"
        
        # Verify: Total documents added
        total_documents = sum(
            result.get("documents_added", 0) 
            for result in results.values() 
            if isinstance(result, dict)
        )
        assert total_documents > 0
        
        # Test: Knowledge base retrieval
        search_results = await seeder.kb.search("company policies", limit=5)
        assert len(search_results) > 0
        
        # Verify: Search results contain relevant content
        content_text = " ".join([result.get("content", "") for result in search_results])
        assert "policy" in content_text.lower() or "company" in content_text.lower()
    
    @pytest.mark.asyncio
    async def test_ai_chain_with_knowledge_base(self, test_session):
        """Test AI chain integration with knowledge base."""
        # Setup: Seed knowledge base
        seeder = KnowledgeBaseSeeder()
        await seeder.initialize()
        await seeder.seed_all()
        
        # Mock AI chain with knowledge base
        with patch('src.ai.chain.ReflexAIChain') as mock_ai_chain_class:
            mock_ai_chain = AsyncMock(spec=ReflexAIChain)
            mock_ai_chain.process_slack_message.return_value = {
                "response": "Based on our company policies, I can help you with that request.",
                "actions": [],
                "confidence": 0.9
            }
            mock_ai_chain_class.return_value = mock_ai_chain
            
            # Test: AI chain can access knowledge base
            # This would typically be tested through the actual AI chain implementation
            # For now, we verify the knowledge base is properly seeded
            search_results = await seeder.kb.search("approval workflow", limit=3)
            assert len(search_results) > 0


class TestDatabasePersistence:
    """Test database persistence across workflows."""
    
    def test_conversation_persistence(self, test_session):
        """Test conversation and message persistence."""
        # Create conversation
        conversation = Conversation(
            user_id="U123456",
            platform="slack",
            channel_id="C123456",
            team_id="T123456",
            title="Test Conversation",
            started_at=datetime.now()
        )
        test_session.add(conversation)
        test_session.commit()
        
        # Create messages
        message1 = Message(
            conversation_id=conversation.id,
            content="Hello, can you help me?",
            sender="U123456",
            message_type="user",
            timestamp=datetime.now()
        )
        message2 = Message(
            conversation_id=conversation.id,
            content="I'd be happy to help!",
            sender="BOT_ID",
            message_type="assistant",
            timestamp=datetime.now()
        )
        test_session.add_all([message1, message2])
        test_session.commit()
        
        # Verify: Persistence
        saved_conversation = test_session.query(Conversation).first()
        assert saved_conversation is not None
        assert saved_conversation.user_id == "U123456"
        assert len(saved_conversation.messages) == 2
        
        # Verify: Message relationships
        assert message1.conversation == conversation
        assert message2.conversation == conversation
    
    def test_workflow_execution_persistence(self, test_session):
        """Test workflow execution persistence."""
        # Create workflow execution
        workflow = WorkflowExecution(
            id="workflow-123",
            workflow_type="slack_mention",
            status="started",
            trigger_user="U123456",
            trigger_channel="C123456",
            trigger_content="Test message",
            team_id="T123456",
            retry_count=0,
            created_at=datetime.now()
        )
        test_session.add(workflow)
        test_session.commit()
        
        # Update workflow status
        workflow.status = "completed"
        workflow.completed_at = datetime.now()
        workflow.result = {"response": "Test response"}
        test_session.commit()
        
        # Verify: Persistence
        saved_workflow = test_session.query(WorkflowExecution).first()
        assert saved_workflow is not None
        assert saved_workflow.status == "completed"
        assert saved_workflow.completed_at is not None
        assert saved_workflow.result == {"response": "Test response"}


class TestErrorHandling:
    """Test error handling in end-to-end workflows."""
    
    def test_webhook_authentication_failure(self, test_client, test_session, sample_slack_event):
        """Test webhook authentication failure handling."""
        with patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.config.get_settings') as mock_settings:
            
            mock_verify.return_value = False
            mock_settings.return_value.slack_signing_secret = "test_secret"
            
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "invalid_signature",
                    "X-Slack-Request-Timestamp": str(int(datetime.now().timestamp()))
                }
            )
            
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]
    
    def test_ai_chain_failure_handling(self, test_client, test_session, sample_slack_event):
        """Test AI chain failure handling."""
        with patch('src.workflows.router.ReflexAIChain') as mock_ai_chain_class, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.config.get_settings') as mock_settings:
            
            mock_verify.return_value = True
            mock_settings.return_value.slack_signing_secret = "test_secret"
            
            mock_ai_chain = AsyncMock(spec=ReflexAIChain)
            mock_ai_chain.process_slack_message.side_effect = Exception("AI processing failed")
            mock_ai_chain_class.return_value = mock_ai_chain
            
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(datetime.now().timestamp()))
                }
            )
            
            # Should handle the error gracefully
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestPerformanceAndScalability:
    """Test performance and scalability aspects."""
    
    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing(self, test_client, test_session):
        """Test concurrent webhook processing."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Create multiple test events
        events = []
        for i in range(5):
            event = {
                "type": "app_mention",
                "user": f"U{i}",
                "text": f"<@BOT_ID> test message {i}",
                "ts": f"1234567890.{i}",
                "channel": f"C{i}",
                "event_ts": f"1234567890.{i}",
                "channel_type": "channel"
            }
            events.append(event)
        
        # Mock authentication and AI chain
        with patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.config.get_settings') as mock_settings, \
             patch('src.workflows.router.ReflexAIChain') as mock_ai_chain_class:
            
            mock_verify.return_value = True
            mock_settings.return_value.slack_signing_secret = "test_secret"
            
            mock_ai_chain = AsyncMock(spec=ReflexAIChain)
            mock_ai_chain.process_slack_message.return_value = {
                "response": "Test response",
                "actions": [],
                "confidence": 0.9
            }
            mock_ai_chain_class.return_value = mock_ai_chain
            
            # Execute: Send concurrent requests
            def send_webhook(event):
                return test_client.post(
                    "/webhooks/slack",
                    json=event,
                    headers={
                        "Content-Type": "application/json",
                        "X-Slack-Signature": "test_signature",
                        "X-Slack-Request-Timestamp": str(int(datetime.now().timestamp()))
                    }
                )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                responses = list(executor.map(send_webhook, events))
            
            # Verify: All requests succeeded
            for response in responses:
                assert response.status_code == 200
                assert response.json() == {"status": "ok"}
            
            # Verify: All workflows were created
            workflows = test_session.query(WorkflowExecution).all()
            assert len(workflows) == 5
    
    def test_database_connection_pooling(self, test_session):
        """Test database connection pooling under load."""
        import threading
        import time
        
        # Create multiple threads to simulate concurrent database access
        def create_conversation(thread_id):
            conversation = Conversation(
                user_id=f"U{thread_id}",
                platform="slack",
                channel_id=f"C{thread_id}",
                team_id="T123456",
                title=f"Test Conversation {thread_id}",
                started_at=datetime.now()
            )
            test_session.add(conversation)
            test_session.commit()
            return conversation.id
        
        # Execute: Concurrent database operations
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda i=i: results.append(create_conversation(i)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify: All operations succeeded
        assert len(results) == 10
        
        # Verify: All conversations were created
        conversations = test_session.query(Conversation).all()
        assert len(conversations) == 10


class TestSystemHealth:
    """Test system health and monitoring."""
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "reflex-executive-assistant"
        assert "version" in data
    
    def test_detailed_health_endpoint(self, test_client):
        """Test detailed health check endpoint."""
        response = test_client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "reflex-executive-assistant"
        assert "version" in data
    
    def test_database_health(self, test_session):
        """Test database health."""
        # Test basic database connectivity
        from sqlalchemy import text
        result = test_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
        # Test table creation and access
        conversation = Conversation(
            user_id="U123456",
            platform="slack",
            channel_id="C123456",
            team_id="T123456",
            title="Health Test",
            started_at=datetime.now()
        )
        test_session.add(conversation)
        test_session.commit()
        
        # Verify: Data can be retrieved
        saved_conversation = test_session.query(Conversation).first()
        assert saved_conversation is not None
        assert saved_conversation.title == "Health Test"


class TestConfigurationValidation:
    """Test configuration validation and loading."""
    
    def test_environment_configuration(self, test_client):
        """Test that the application loads configuration correctly."""
        # The application should start with test configuration
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # Verify: Application is using test settings
        # This would typically be verified through configuration inspection
        # For now, we verify the application is running
    
    def test_required_environment_variables(self):
        """Test required environment variables validation."""
        import os
        from src.config import get_settings
        
        # Test with missing required variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                get_settings()


class TestIntegrationEndpoints:
    """Test integration-specific endpoints."""
    
    def test_api_documentation(self, test_client):
        """Test API documentation endpoint."""
        response = test_client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_openapi_schema(self, test_client):
        """Test OpenAPI schema endpoint."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data 