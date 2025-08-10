"""Unit tests for configuration module."""

import pytest
import os
from unittest.mock import patch
from src.config import get_settings, is_production, is_development, is_testing


class TestConfig:
    """Test configuration management."""
    
    def test_get_settings_defaults(self):
        """Test that settings are loaded with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
            
            assert settings.app_env == "dev"
            assert settings.port == 8080
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.model_name == "gpt-4o-mini"
            assert settings.model_temperature == 0.1
            assert settings.model_max_tokens == 4000
    
    def test_get_settings_from_env(self):
        """Test that settings are loaded from environment variables."""
        env_vars = {
            "APP_ENV": "production",
            "PORT": "9000",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "MODEL_NAME": "gpt-4",
            "MODEL_TEMPERATURE": "0.5",
            "MODEL_MAX_TOKENS": "8000",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = get_settings()
            
            assert settings.app_env == "production"
            assert settings.port == 9000
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.model_name == "gpt-4"
            assert settings.model_temperature == 0.5
            assert settings.model_max_tokens == 8000
            assert settings.openai_api_key == "test-key"
            assert settings.pinecone_api_key == "test-pinecone-key"
            assert settings.pinecone_env == "us-east-1"
            assert settings.pinecone_index == "test-index"
            assert settings.postgres_url == "postgresql://test:test@localhost/test"
            assert settings.redis_url == "redis://localhost:6379/0"
            assert settings.google_client_id == "test-client-id"
            assert settings.google_client_secret == "test-client-secret"
            assert settings.google_redirect_uri == "http://localhost:8080/oauth/callback"
            assert settings.slack_bot_token == "xoxb-test-token"
            assert settings.slack_signing_secret == "test-signing-secret"
            assert settings.slack_app_level_token == "xapp-test-token"
            assert settings.slack_verification_token == "test-verification-token"
            assert settings.asana_access_token == "test-asana-token"
            assert settings.asana_workspace_id == "test-workspace-id"
            assert settings.asana_webhook_secret == "test-webhook-secret"
            assert settings.secret_key == "test-secret-key-32-chars-minimum"
            assert settings.jwt_secret == "test-jwt-secret-32-chars-minimum"
            assert settings.webhook_base_url == "http://localhost:8080"
            assert settings.smtp_username == "test@example.com"
            assert settings.smtp_password == "test-password"
            assert settings.celery_broker_url == "redis://localhost:6379/1"
            assert settings.celery_result_backend == "redis://localhost:6379/2"
    
    def test_excluded_markets_parsing(self):
        """Test that excluded markets are parsed correctly."""
        env_vars = {
            "EXCLUDED_MARKETS": "therapeutic,wellness,medical,pharma",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = get_settings()
            
            assert "therapeutic" in settings.excluded_markets
            assert "wellness" in settings.excluded_markets
            assert "medical" in settings.excluded_markets
            assert "pharma" in settings.excluded_markets
            assert len(settings.excluded_markets) == 4
    
    def test_celery_accept_content_parsing(self):
        """Test that Celery accept content is parsed correctly."""
        env_vars = {
            "CELERY_ACCEPT_CONTENT": "json,pickle,yaml",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = get_settings()
            
            assert "json" in settings.celery_accept_content
            assert "pickle" in settings.celery_accept_content
            assert "yaml" in settings.celery_accept_content
            assert len(settings.celery_accept_content) == 3
    
    def test_secret_key_validation(self):
        """Test that secret key validation works."""
        env_vars = {
            "SECRET_KEY": "short",  # Too short
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters long"):
                get_settings()
    
    def test_postgres_url_validation(self):
        """Test that PostgreSQL URL validation works."""
        env_vars = {
            "POSTGRES_URL": "invalid-url",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="POSTGRES_URL must start with postgresql:// or postgresql\\+psycopg2://"):
                get_settings()
    
    def test_redis_url_validation(self):
        """Test that Redis URL validation works."""
        env_vars = {
            "REDIS_URL": "invalid-url",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="REDIS_URL must start with redis://"):
                get_settings()
    
    def test_slack_bot_token_validation(self):
        """Test that Slack bot token validation works."""
        env_vars = {
            "SLACK_BOT_TOKEN": "invalid-token",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-test-token",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="SLACK_BOT_TOKEN must start with xoxb-"):
                get_settings()
    
    def test_slack_app_level_token_validation(self):
        """Test that Slack app level token validation works."""
        env_vars = {
            "SLACK_APP_LEVEL_TOKEN": "invalid-token",
            "OPENAI_API_KEY": "test-key",
            "PINECONE_API_KEY": "test-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "test-index",
            "POSTGRES_URL": "postgresql://test:test@localhost/test",
            "REDIS_URL": "redis://localhost:6379/0",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "SLACK_VERIFICATION_TOKEN": "test-verification-token",
            "ASANA_ACCESS_TOKEN": "test-asana-token",
            "ASANA_WORKSPACE_ID": "test-workspace-id",
            "ASANA_WEBHOOK_SECRET": "test-webhook-secret",
            "SECRET_KEY": "test-secret-key-32-chars-minimum",
            "JWT_SECRET": "test-jwt-secret-32-chars-minimum",
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            "SMTP_USERNAME": "test@example.com",
            "SMTP_PASSWORD": "test-password",
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="SLACK_APP_LEVEL_TOKEN must start with xapp-"):
                get_settings()
    
    def test_environment_functions(self):
        """Test environment detection functions."""
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            assert is_production() is True
            assert is_development() is False
            assert is_testing() is False
        
        with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
            assert is_production() is False
            assert is_development() is True
            assert is_testing() is False
        
        with patch.dict(os.environ, {"APP_ENV": "test"}, clear=True):
            assert is_production() is False
            assert is_development() is False
            assert is_testing() is True 