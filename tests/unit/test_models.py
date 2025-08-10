"""Unit tests for database models."""

import pytest
from datetime import datetime, date, time
from sqlalchemy.exc import IntegrityError
from src.storage.models import (
    Conversation, Message, WorkflowExecution, SlackChannel, SlackUser, 
    SlackMessage, Email, AsanaProject, AsanaTask, AsanaStory
)


class TestConversation:
    """Test Conversation model."""
    
    def test_create_conversation(self, test_session):
        """Test creating a conversation."""
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
        
        assert conversation.id is not None
        assert conversation.user_id == "U123456"
        assert conversation.platform == "slack"
        assert conversation.channel_id == "C123456"
        assert conversation.team_id == "T123456"
        assert conversation.title == "Test Conversation"
        assert conversation.workflow_id is None
    
    def test_conversation_required_fields(self, test_session):
        """Test that required fields are enforced."""
        conversation = Conversation(
            # Missing required fields
            title="Test Conversation"
        )
        
        with pytest.raises(IntegrityError):
            test_session.add(conversation)
            test_session.commit()
    
    def test_conversation_relationships(self, test_session):
        """Test conversation relationships with messages."""
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
            content="Hello",
            sender="U123456",
            message_type="user",
            timestamp=datetime.now()
        )
        message2 = Message(
            conversation_id=conversation.id,
            content="Hi there!",
            sender="BOT_ID",
            message_type="assistant",
            timestamp=datetime.now()
        )
        
        test_session.add_all([message1, message2])
        test_session.commit()
        
        # Test relationships
        assert len(conversation.messages) == 2
        assert conversation.messages[0].content == "Hello"
        assert conversation.messages[1].content == "Hi there!"
        assert message1.conversation == conversation
        assert message2.conversation == conversation


class TestMessage:
    """Test Message model."""
    
    def test_create_message(self, test_session):
        """Test creating a message."""
        # Create conversation first
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
        
        # Create message
        message = Message(
            conversation_id=conversation.id,
            content="Test message content",
            sender="U123456",
            message_type="user",
            metadata={"key": "value"},
            timestamp=datetime.now()
        )
        
        test_session.add(message)
        test_session.commit()
        
        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.content == "Test message content"
        assert message.sender == "U123456"
        assert message.message_type == "user"
        assert message.metadata == {"key": "value"}
    
    def test_message_required_fields(self, test_session):
        """Test that required fields are enforced."""
        message = Message(
            # Missing required fields
            content="Test message"
        )
        
        with pytest.raises(IntegrityError):
            test_session.add(message)
            test_session.commit()


class TestWorkflowExecution:
    """Test WorkflowExecution model."""
    
    def test_create_workflow_execution(self, test_session):
        """Test creating a workflow execution."""
        workflow = WorkflowExecution(
            id="workflow-123",
            workflow_type="slack_mention",
            status="started",
            trigger_user="U123456",
            trigger_channel="C123456",
            trigger_content="Test message",
            team_id="T123456",
            result={"response": "Test response"},
            retry_count=0,
            created_at=datetime.now()
        )
        
        test_session.add(workflow)
        test_session.commit()
        
        assert workflow.id == "workflow-123"
        assert workflow.workflow_type == "slack_mention"
        assert workflow.status == "started"
        assert workflow.trigger_user == "U123456"
        assert workflow.trigger_channel == "C123456"
        assert workflow.trigger_content == "Test message"
        assert workflow.team_id == "T123456"
        assert workflow.result == {"response": "Test response"}
        assert workflow.retry_count == 0
        assert workflow.error_message is None
        assert workflow.started_at is None
        assert workflow.completed_at is None
    
    def test_workflow_execution_status_transitions(self, test_session):
        """Test workflow execution status transitions."""
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
        
        # Update status
        workflow.status = "completed"
        workflow.completed_at = datetime.now()
        test_session.commit()
        
        assert workflow.status == "completed"
        assert workflow.completed_at is not None


class TestSlackChannel:
    """Test SlackChannel model."""
    
    def test_create_slack_channel(self, test_session):
        """Test creating a Slack channel."""
        channel = SlackChannel(
            id="C123456",
            name="general",
            team_id="T123456",
            is_private=False,
            is_archived=False,
            member_count=10,
            topic="General discussion",
            purpose="Team communication",
            created_at=datetime.now()
        )
        
        test_session.add(channel)
        test_session.commit()
        
        assert channel.id == "C123456"
        assert channel.name == "general"
        assert channel.team_id == "T123456"
        assert channel.is_private is False
        assert channel.is_archived is False
        assert channel.member_count == 10
        assert channel.topic == "General discussion"
        assert channel.purpose == "Team communication"
    
    def test_slack_channel_relationships(self, test_session):
        """Test Slack channel relationships with messages."""
        # Create channel
        channel = SlackChannel(
            id="C123456",
            name="general",
            team_id="T123456",
            is_private=False,
            is_archived=False,
            created_at=datetime.now()
        )
        test_session.add(channel)
        test_session.commit()
        
        # Create user
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
        
        # Create message
        message = SlackMessage(
            id="msg-123",
            channel_id=channel.id,
            user_id=user.id,
            text="Test message",
            ts="1234567890.123456",
            type="message",
            timestamp=datetime.now()
        )
        test_session.add(message)
        test_session.commit()
        
        # Test relationships
        assert len(channel.messages) == 1
        assert channel.messages[0].text == "Test message"
        assert message.channel == channel
        assert message.user == user


class TestSlackUser:
    """Test SlackUser model."""
    
    def test_create_slack_user(self, test_session):
        """Test creating a Slack user."""
        user = SlackUser(
            id="U123456",
            team_id="T123456",
            name="testuser",
            real_name="Test User",
            email="test@example.com",
            is_bot=False,
            is_admin=False,
            status="active",
            status_text="Available",
            created_at=datetime.now()
        )
        
        test_session.add(user)
        test_session.commit()
        
        assert user.id == "U123456"
        assert user.team_id == "T123456"
        assert user.name == "testuser"
        assert user.real_name == "Test User"
        assert user.email == "test@example.com"
        assert user.is_bot is False
        assert user.is_admin is False
        assert user.status == "active"
        assert user.status_text == "Available"


class TestEmail:
    """Test Email model."""
    
    def test_create_email(self, test_session):
        """Test creating an email."""
        email = Email(
            id="email-123",
            thread_id="thread-123",
            from_email="sender@example.com",
            to_emails="recipient@example.com",
            cc_emails="cc@example.com",
            bcc_emails="bcc@example.com",
            subject="Test Email",
            body="Test email body",
            body_plain="Test email body plain",
            body_html="<p>Test email body</p>",
            labels="INBOX,IMPORTANT",
            is_read=False,
            is_important=True,
            has_attachments=False,
            metadata={"message_id": "msg-123"},
            received_at=datetime.now()
        )
        
        test_session.add(email)
        test_session.commit()
        
        assert email.id == "email-123"
        assert email.thread_id == "thread-123"
        assert email.from_email == "sender@example.com"
        assert email.to_emails == "recipient@example.com"
        assert email.cc_emails == "cc@example.com"
        assert email.bcc_emails == "bcc@example.com"
        assert email.subject == "Test Email"
        assert email.body == "Test email body"
        assert email.body_plain == "Test email body plain"
        assert email.body_html == "<p>Test email body</p>"
        assert email.labels == "INBOX,IMPORTANT"
        assert email.is_read is False
        assert email.is_important is True
        assert email.has_attachments is False
        assert email.metadata == {"message_id": "msg-123"}


class TestAsanaProject:
    """Test AsanaProject model."""
    
    def test_create_asana_project(self, test_session):
        """Test creating an Asana project."""
        project = AsanaProject(
            id="project-123",
            name="Test Project",
            description="Test project description",
            workspace_id="workspace-123",
            team_id="team-123",
            owner_id="user-123",
            color="blue",
            default_view="list",
            due_date=date(2024, 12, 31),
            start_on=date(2024, 1, 1),
            is_public=True,
            is_archived=False,
            metadata={"custom_field": "value"},
            created_at=datetime.now()
        )
        
        test_session.add(project)
        test_session.commit()
        
        assert project.id == "project-123"
        assert project.name == "Test Project"
        assert project.description == "Test project description"
        assert project.workspace_id == "workspace-123"
        assert project.team_id == "team-123"
        assert project.owner_id == "user-123"
        assert project.color == "blue"
        assert project.default_view == "list"
        assert project.due_date == date(2024, 12, 31)
        assert project.start_on == date(2024, 1, 1)
        assert project.is_public is True
        assert project.is_archived is False
        assert project.metadata == {"custom_field": "value"}


class TestAsanaTask:
    """Test AsanaTask model."""
    
    def test_create_asana_task(self, test_session):
        """Test creating an Asana task."""
        # Create project first
        project = AsanaProject(
            id="project-123",
            name="Test Project",
            workspace_id="workspace-123",
            is_public=True,
            is_archived=False,
            created_at=datetime.now()
        )
        test_session.add(project)
        test_session.commit()
        
        # Create task
        task = AsanaTask(
            id="task-123",
            name="Test Task",
            description="Test task description",
            project_id=project.id,
            section_id="section-123",
            assignee_id="user-123",
            created_by_id="user-456",
            due_date=date(2024, 12, 31),
            due_time=time(17, 0),
            start_on=date(2024, 1, 1),
            completed_at=datetime.now(),
            is_completed=True,
            priority="high",
            status="in_progress",
            tags="urgent,important",
            metadata={"custom_field": "value"},
            created_at=datetime.now()
        )
        
        test_session.add(task)
        test_session.commit()
        
        assert task.id == "task-123"
        assert task.name == "Test Task"
        assert task.description == "Test task description"
        assert task.project_id == project.id
        assert task.section_id == "section-123"
        assert task.assignee_id == "user-123"
        assert task.created_by_id == "user-456"
        assert task.due_date == date(2024, 12, 31)
        assert task.due_time == time(17, 0)
        assert task.start_on == date(2024, 1, 1)
        assert task.is_completed is True
        assert task.priority == "high"
        assert task.status == "in_progress"
        assert task.tags == "urgent,important"
        assert task.metadata == {"custom_field": "value"}
        assert task.project == project
    
    def test_asana_task_relationships(self, test_session):
        """Test Asana task relationships with stories."""
        # Create project and task
        project = AsanaProject(
            id="project-123",
            name="Test Project",
            workspace_id="workspace-123",
            is_public=True,
            is_archived=False,
            created_at=datetime.now()
        )
        test_session.add(project)
        test_session.commit()
        
        task = AsanaTask(
            id="task-123",
            name="Test Task",
            project_id=project.id,
            is_completed=False,
            created_at=datetime.now()
        )
        test_session.add(task)
        test_session.commit()
        
        # Create story
        story = AsanaStory(
            id="story-123",
            task_id=task.id,
            type="comment",
            text="Test comment",
            created_by_id="user-123",
            resource_type="task",
            resource_subtype="comment_added",
            metadata={"comment_id": "comment-123"},
            created_at=datetime.now()
        )
        test_session.add(story)
        test_session.commit()
        
        # Test relationships
        assert len(task.stories) == 1
        assert task.stories[0].text == "Test comment"
        assert story.task == task


class TestAsanaStory:
    """Test AsanaStory model."""
    
    def test_create_asana_story(self, test_session):
        """Test creating an Asana story."""
        # Create project and task first
        project = AsanaProject(
            id="project-123",
            name="Test Project",
            workspace_id="workspace-123",
            is_public=True,
            is_archived=False,
            created_at=datetime.now()
        )
        test_session.add(project)
        test_session.commit()
        
        task = AsanaTask(
            id="task-123",
            name="Test Task",
            project_id=project.id,
            is_completed=False,
            created_at=datetime.now()
        )
        test_session.add(task)
        test_session.commit()
        
        # Create story
        story = AsanaStory(
            id="story-123",
            task_id=task.id,
            type="comment",
            text="Test comment",
            created_by_id="user-123",
            resource_type="task",
            resource_subtype="comment_added",
            metadata={"comment_id": "comment-123"},
            created_at=datetime.now()
        )
        
        test_session.add(story)
        test_session.commit()
        
        assert story.id == "story-123"
        assert story.task_id == task.id
        assert story.type == "comment"
        assert story.text == "Test comment"
        assert story.created_by_id == "user-123"
        assert story.resource_type == "task"
        assert story.resource_subtype == "comment_added"
        assert story.metadata == {"comment_id": "comment-123"}
        assert story.task == task 