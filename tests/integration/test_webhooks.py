"""Integration tests for webhook endpoints."""

import pytest
import json
import hmac
import hashlib
import time
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.app import create_app
from src.storage.models import Conversation, Message, WorkflowExecution


class TestSlackWebhook:
    """Test Slack webhook endpoint."""
    
    def test_slack_url_verification(self, test_client, test_session):
        """Test Slack URL verification challenge."""
        challenge_data = {
            "type": "url_verification",
            "challenge": "test_challenge_string",
            "token": "test_verification_token"
        }
        
        with patch('src.config.get_settings') as mock_settings:
            mock_settings.return_value.slack_verification_token = "test_verification_token"
            
            response = test_client.post(
                "/webhooks/slack",
                json=challenge_data,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            assert response.json() == {"challenge": "test_challenge_string"}
    
    def test_slack_event_processing(self, test_client, test_session, sample_slack_event):
        """Test Slack event processing."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.workflows.router.route_slack_event') as mock_route:
            
            mock_settings.return_value.slack_signing_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.return_value = {"status": "processed"}
            
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time()))
                }
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            mock_route.assert_called_once()
    
    def test_slack_invalid_signature(self, test_client, test_session, sample_slack_event):
        """Test Slack webhook with invalid signature."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify:
            
            mock_settings.return_value.slack_signing_secret = "test_secret"
            mock_verify.return_value = False
            
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "invalid_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time()))
                }
            )
            
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]
    
    def test_slack_bot_message_ignored(self, test_client, test_session):
        """Test that bot messages are ignored."""
        bot_event = {
            "type": "message",
            "user": "BOT_ID",
            "text": "Bot message",
            "ts": "1234567890.123456",
            "channel": "C123456",
            "event_ts": "1234567890.123456",
            "channel_type": "channel"
        }
        
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify:
            
            mock_settings.return_value.slack_signing_secret = "test_secret"
            mock_verify.return_value = True
            
            response = test_client.post(
                "/webhooks/slack",
                json=bot_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time()))
                }
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "ignored"}


class TestGmailWebhook:
    """Test Gmail webhook endpoint."""
    
    def test_gmail_notification_processing(self, test_client, test_session, sample_gmail_notification):
        """Test Gmail notification processing."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.gmail.verify_gmail_signature') as mock_verify, \
             patch('src.workflows.router.route_gmail_notification') as mock_route:
            
            mock_settings.return_value.google_client_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.return_value = {"status": "processed"}
            
            response = test_client.post(
                "/webhooks/gmail",
                json=sample_gmail_notification,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test_token"
                }
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            mock_route.assert_called_once()
    
    def test_gmail_invalid_signature(self, test_client, test_session, sample_gmail_notification):
        """Test Gmail webhook with invalid signature."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.gmail.verify_gmail_signature') as mock_verify:
            
            mock_settings.return_value.google_client_secret = "test_secret"
            mock_verify.return_value = False
            
            response = test_client.post(
                "/webhooks/gmail",
                json=sample_gmail_notification,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer invalid_token"
                }
            )
            
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]
    
    def test_gmail_malformed_notification(self, test_client, test_session):
        """Test Gmail webhook with malformed notification."""
        malformed_notification = {
            "message": {
                "data": "invalid_base64_data",
                "messageId": "1234567890"
            }
        }
        
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.gmail.verify_gmail_signature') as mock_verify:
            
            mock_settings.return_value.google_client_secret = "test_secret"
            mock_verify.return_value = True
            
            response = test_client.post(
                "/webhooks/gmail",
                json=malformed_notification,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test_token"
                }
            )
            
            assert response.status_code == 400
            assert "Invalid notification format" in response.json()["detail"]


class TestAsanaWebhook:
    """Test Asana webhook endpoint."""
    
    def test_asana_event_processing(self, test_client, test_session, sample_asana_event):
        """Test Asana event processing."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.asana.verify_asana_signature') as mock_verify, \
             patch('src.workflows.router.route_asana_event') as mock_route:
            
            mock_settings.return_value.asana_webhook_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.return_value = {"status": "processed"}
            
            response = test_client.post(
                "/webhooks/asana",
                json=sample_asana_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Hook-Signature": "test_signature"
                }
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            mock_route.assert_called_once()
    
    def test_asana_invalid_signature(self, test_client, test_session, sample_asana_event):
        """Test Asana webhook with invalid signature."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.asana.verify_asana_signature') as mock_verify:
            
            mock_settings.return_value.asana_webhook_secret = "test_secret"
            mock_verify.return_value = False
            
            response = test_client.post(
                "/webhooks/asana",
                json=sample_asana_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Hook-Signature": "invalid_signature"
                }
            )
            
            assert response.status_code == 401
            assert "Invalid signature" in response.json()["detail"]
    
    def test_asana_empty_events(self, test_client, test_session):
        """Test Asana webhook with empty events."""
        empty_event = {"events": []}
        
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.asana.verify_asana_signature') as mock_verify:
            
            mock_settings.return_value.asana_webhook_secret = "test_secret"
            mock_verify.return_value = True
            
            response = test_client.post(
                "/webhooks/asana",
                json=empty_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Hook-Signature": "test_signature"
                }
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "ignored"}


class TestWebhookAuthentication:
    """Test webhook authentication mechanisms."""
    
    def test_slack_signature_verification(self):
        """Test Slack signature verification."""
        from src.integrations.webhooks.slack import verify_slack_signature
        
        timestamp = str(int(time.time()))
        body = '{"test": "data"}'
        secret = "test_secret"
        
        # Create valid signature
        sig_basestring = f"v0:{timestamp}:{body}"
        signature = f"v0={hmac.new(secret.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()}"
        
        # Test valid signature
        assert verify_slack_signature(signature, timestamp, body, secret) is True
        
        # Test invalid signature
        assert verify_slack_signature("invalid_signature", timestamp, body, secret) is False
    
    def test_gmail_signature_verification(self):
        """Test Gmail signature verification."""
        from src.integrations.webhooks.gmail import verify_gmail_signature
        
        # Mock JWT verification
        with patch('src.integrations.webhooks.gmail.jwt.decode') as mock_jwt:
            mock_jwt.return_value = {"aud": "test_audience"}
            
            # Test valid signature
            assert verify_gmail_signature("valid_token", "test_secret") is True
            
            # Test invalid signature
            mock_jwt.side_effect = Exception("Invalid token")
            assert verify_gmail_signature("invalid_token", "test_secret") is False
    
    def test_asana_signature_verification(self):
        """Test Asana signature verification."""
        from src.integrations.webhooks.asana import verify_asana_signature
        
        body = '{"test": "data"}'
        secret = "test_secret"
        
        # Create valid signature
        signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        
        # Test valid signature
        assert verify_asana_signature(signature, body, secret) is True
        
        # Test invalid signature
        assert verify_asana_signature("invalid_signature", body, secret) is False


class TestWebhookErrorHandling:
    """Test webhook error handling."""
    
    def test_slack_webhook_exception_handling(self, test_client, test_session, sample_slack_event):
        """Test Slack webhook exception handling."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.workflows.router.route_slack_event') as mock_route:
            
            mock_settings.return_value.slack_signing_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.side_effect = Exception("Processing error")
            
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time()))
                }
            )
            
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
    
    def test_gmail_webhook_exception_handling(self, test_client, test_session, sample_gmail_notification):
        """Test Gmail webhook exception handling."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.gmail.verify_gmail_signature') as mock_verify, \
             patch('src.workflows.router.route_gmail_notification') as mock_route:
            
            mock_settings.return_value.google_client_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.side_effect = Exception("Processing error")
            
            response = test_client.post(
                "/webhooks/gmail",
                json=sample_gmail_notification,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test_token"
                }
            )
            
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
    
    def test_asana_webhook_exception_handling(self, test_client, test_session, sample_asana_event):
        """Test Asana webhook exception handling."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.asana.verify_asana_signature') as mock_verify, \
             patch('src.workflows.router.route_asana_event') as mock_route:
            
            mock_settings.return_value.asana_webhook_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.side_effect = Exception("Processing error")
            
            response = test_client.post(
                "/webhooks/asana",
                json=sample_asana_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Hook-Signature": "test_signature"
                }
            )
            
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]


class TestWebhookDataPersistence:
    """Test webhook data persistence."""
    
    def test_slack_event_persistence(self, test_client, test_session, sample_slack_event):
        """Test that Slack events are persisted to database."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.slack.verify_slack_signature') as mock_verify, \
             patch('src.workflows.router.route_slack_event') as mock_route:
            
            mock_settings.return_value.slack_signing_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.return_value = {"status": "processed"}
            
            # Send webhook
            response = test_client.post(
                "/webhooks/slack",
                json=sample_slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time()))
                }
            )
            
            assert response.status_code == 200
            
            # Check that workflow execution was created
            workflow = test_session.query(WorkflowExecution).first()
            assert workflow is not None
            assert workflow.workflow_type == "slack_mention"
            assert workflow.trigger_user == "U123456"
            assert workflow.trigger_channel == "C123456"
    
    def test_gmail_notification_persistence(self, test_client, test_session, sample_gmail_notification):
        """Test that Gmail notifications are persisted to database."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.gmail.verify_gmail_signature') as mock_verify, \
             patch('src.workflows.router.route_gmail_notification') as mock_route:
            
            mock_settings.return_value.google_client_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.return_value = {"status": "processed"}
            
            # Send webhook
            response = test_client.post(
                "/webhooks/gmail",
                json=sample_gmail_notification,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test_token"
                }
            )
            
            assert response.status_code == 200
            
            # Check that workflow execution was created
            workflow = test_session.query(WorkflowExecution).first()
            assert workflow is not None
            assert workflow.workflow_type == "email_notification"
    
    def test_asana_event_persistence(self, test_client, test_session, sample_asana_event):
        """Test that Asana events are persisted to database."""
        with patch('src.config.get_settings') as mock_settings, \
             patch('src.integrations.webhooks.asana.verify_asana_signature') as mock_verify, \
             patch('src.workflows.router.route_asana_event') as mock_route:
            
            mock_settings.return_value.asana_webhook_secret = "test_secret"
            mock_verify.return_value = True
            mock_route.return_value = {"status": "processed"}
            
            # Send webhook
            response = test_client.post(
                "/webhooks/asana",
                json=sample_asana_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Hook-Signature": "test_signature"
                }
            )
            
            assert response.status_code == 200
            
            # Check that workflow execution was created
            workflow = test_session.query(WorkflowExecution).first()
            assert workflow is not None
            assert workflow.workflow_type == "asana_update" 