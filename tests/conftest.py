"""Pytest configuration and fixtures for Reflex Executive Assistant."""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app import create_app
from src.config import get_settings
from src.storage.models import Base
from src.storage.db import get_db_session
from src.ai.chain import ReflexAIChain
from src.kb.retriever import KnowledgeBaseRetriever


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings with in-memory database."""
    settings = get_settings()
    settings.postgres_url = "sqlite:///:memory:"
    settings.app_env = "test"
    settings.debug = True
    return settings


@pytest.fixture
def test_engine(test_settings):
    """Create test database engine."""
    engine = create_engine(
        test_settings.postgres_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_db_session(test_session):
    """Mock database session for dependency injection."""
    def _get_test_db():
        try:
            yield test_session
        finally:
            pass
    
    return _get_test_db


@pytest.fixture
def test_client(mock_db_session) -> Generator:
    """Create test client with mocked dependencies."""
    app = create_app()
    
    # Override database dependency
    app.dependency_overrides[get_db_session] = mock_db_session
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_ai_chain():
    """Mock AI chain for testing."""
    chain = Mock(spec=ReflexAIChain)
    chain.process_slack_message = AsyncMock(return_value={
        "response": "Test response",
        "actions": [],
        "confidence": 0.9
    })
    chain.process_email = AsyncMock(return_value={
        "response": "Email processed",
        "actions": [],
        "confidence": 0.8
    })
    chain.process_asana_update = AsyncMock(return_value={
        "response": "Asana update processed",
        "actions": [],
        "confidence": 0.85
    })
    return chain


@pytest.fixture
def mock_knowledge_base():
    """Mock knowledge base for testing."""
    kb = Mock(spec=KnowledgeBaseRetriever)
    kb.search = AsyncMock(return_value=[
        {"content": "Test knowledge", "metadata": {"source": "test"}}
    ])
    kb.add_document = AsyncMock(return_value=True)
    return kb


@pytest.fixture
def mock_slack_client():
    """Mock Slack client for testing."""
    client = Mock()
    client.send_message = AsyncMock(return_value={"ok": True})
    client.get_channel_info = AsyncMock(return_value={
        "id": "C123456",
        "name": "test-channel",
        "is_private": False
    })
    client.get_user_info = AsyncMock(return_value={
        "id": "U123456",
        "name": "testuser",
        "real_name": "Test User"
    })
    return client


@pytest.fixture
def mock_gmail_client():
    """Mock Gmail client for testing."""
    client = Mock()
    client.send_email = AsyncMock(return_value={"id": "test-email-id"})
    client.search_emails = AsyncMock(return_value=[
        {"id": "email1", "subject": "Test Email"}
    ])
    client.compose_email = AsyncMock(return_value={"id": "draft-id"})
    return client


@pytest.fixture
def mock_asana_client():
    """Mock Asana client for testing."""
    client = Mock()
    client.create_task = AsyncMock(return_value={"id": "task-123"})
    client.update_task = AsyncMock(return_value={"id": "task-123"})
    client.get_project = AsyncMock(return_value={
        "id": "project-123",
        "name": "Test Project"
    })
    return client


@pytest.fixture
def sample_slack_event():
    """Sample Slack event for testing."""
    return {
        "type": "app_mention",
        "user": "U123456",
        "text": "<@BOT_ID> hello",
        "ts": "1234567890.123456",
        "channel": "C123456",
        "event_ts": "1234567890.123456",
        "channel_type": "channel"
    }


@pytest.fixture
def sample_gmail_notification():
    """Sample Gmail notification for testing."""
    return {
        "message": {
            "data": "eyJlbWFpbEFkZHJlc3MiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibWVzc2FnZUlkIjoiMTIzNDU2Nzg5MCJ9",
            "messageId": "1234567890",
            "publishTime": "2024-01-01T00:00:00.000Z"
        },
        "subscription": "projects/test-project/subscriptions/gmail-notifications"
    }


@pytest.fixture
def sample_asana_event():
    """Sample Asana event for testing."""
    return {
        "events": [
            {
                "action": "changed",
                "resource": {
                    "id": "task-123",
                    "name": "Test Task",
                    "resource_type": "task"
                },
                "parent": {
                    "id": "project-123",
                    "name": "Test Project",
                    "resource_type": "project"
                },
                "user": {
                    "id": "user-123",
                    "name": "Test User"
                },
                "created_at": "2024-01-01T00:00:00.000Z"
            }
        ]
    }


@pytest.fixture
def sample_workflow_execution():
    """Sample workflow execution for testing."""
    return {
        "id": "workflow-123",
        "workflow_type": "slack_mention",
        "status": "started",
        "trigger_user": "U123456",
        "trigger_channel": "C123456",
        "trigger_content": "Test message",
        "team_id": "T123456",
        "created_at": "2024-01-01T00:00:00.000Z"
    }


@pytest.fixture
def sample_conversation():
    """Sample conversation for testing."""
    return {
        "user_id": "U123456",
        "platform": "slack",
        "channel_id": "C123456",
        "team_id": "T123456",
        "title": "Test Conversation",
        "started_at": "2024-01-01T00:00:00.000Z"
    }


@pytest.fixture
def sample_message():
    """Sample message for testing."""
    return {
        "content": "Test message content",
        "sender": "U123456",
        "message_type": "user",
        "timestamp": "2024-01-01T00:00:00.000Z"
    }


# Test data fixtures
@pytest.fixture
def test_users():
    """Test user data."""
    return [
        {
            "id": "U123456",
            "name": "testuser1",
            "real_name": "Test User 1",
            "email": "user1@example.com"
        },
        {
            "id": "U789012",
            "name": "testuser2",
            "real_name": "Test User 2",
            "email": "user2@example.com"
        }
    ]


@pytest.fixture
def test_channels():
    """Test channel data."""
    return [
        {
            "id": "C123456",
            "name": "general",
            "team_id": "T123456",
            "is_private": False
        },
        {
            "id": "C789012",
            "name": "random",
            "team_id": "T123456",
            "is_private": False
        }
    ]


@pytest.fixture
def test_projects():
    """Test project data."""
    return [
        {
            "id": "project-123",
            "name": "Test Project 1",
            "workspace_id": "workspace-123",
            "description": "Test project description"
        },
        {
            "id": "project-456",
            "name": "Test Project 2",
            "workspace_id": "workspace-123",
            "description": "Another test project"
        }
    ]


@pytest.fixture
def test_tasks():
    """Test task data."""
    return [
        {
            "id": "task-123",
            "name": "Test Task 1",
            "project_id": "project-123",
            "assignee_id": "user-123",
            "due_date": "2024-12-31"
        },
        {
            "id": "task-456",
            "name": "Test Task 2",
            "project_id": "project-123",
            "assignee_id": "user-456",
            "due_date": "2024-12-30"
        }
    ]


# Utility functions for testing
def create_test_conversation(session, **kwargs):
    """Helper function to create a test conversation."""
    from src.storage.models import Conversation
    
    conversation = Conversation(**kwargs)
    session.add(conversation)
    session.commit()
    return conversation


def create_test_message(session, conversation_id, **kwargs):
    """Helper function to create a test message."""
    from src.storage.models import Message
    
    message = Message(conversation_id=conversation_id, **kwargs)
    session.add(message)
    session.commit()
    return message


def create_test_workflow_execution(session, **kwargs):
    """Helper function to create a test workflow execution."""
    from src.storage.models import WorkflowExecution
    
    workflow = WorkflowExecution(**kwargs)
    session.add(workflow)
    session.commit()
    return workflow 