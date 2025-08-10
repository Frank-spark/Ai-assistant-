#!/usr/bin/env python3
"""Reflex AI Assistant Starter Pack - Complete demo setup."""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings


class StarterPack:
    """Complete starter pack for Reflex AI Assistant."""
    
    def __init__(self):
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.demos_dir = project_root / "demos"
        self.config_dir = project_root / "config"
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.demos_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
    
    def setup_demo_environment(self, deployment_type: str = "docker"):
        """Setup complete demo environment."""
        print("🚀 Setting up Reflex AI Assistant Demo Environment...")
        
        try:
            # 1. Create demo configuration
            self._create_demo_config()
            
            # 2. Setup sample data
            self._setup_sample_data()
            
            # 3. Create demo knowledge base
            self._create_demo_kb()
            
            # 4. Setup integrations
            self._setup_demo_integrations()
            
            # 5. Create deployment files
            self._create_deployment_files(deployment_type)
            
            # 6. Setup monitoring
            self._setup_monitoring()
            
            print("✅ Demo environment setup complete!")
            self._print_next_steps(deployment_type)
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            sys.exit(1)
    
    def _create_demo_config(self):
        """Create demo configuration files."""
        print("📝 Creating demo configuration...")
        
        # Demo environment file
        demo_env = {
            "APP_ENV": "demo",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "PORT": "8080",
            "SECRET_KEY": "demo-secret-key-32-chars-minimum-for-testing",
            "JWT_SECRET": "demo-jwt-secret-32-chars-minimum-for-testing",
            
            # Database
            "POSTGRES_URL": "postgresql://reflex_user:reflex_password@localhost:5432/reflex_demo",
            
            # Redis
            "REDIS_URL": "redis://localhost:6379/0",
            
            # AI Models
            "OPENAI_API_KEY": "demo-openai-key",
            "MODEL_NAME": "gpt-4o-mini",
            "MODEL_TEMPERATURE": "0.7",
            "MODEL_MAX_TOKENS": "4000",
            
            # Vector Database
            "PINECONE_API_KEY": "demo-pinecone-key",
            "PINECONE_ENV": "us-east-1",
            "PINECONE_INDEX": "reflex-demo",
            
            # External Integrations
            "SLACK_BOT_TOKEN": "xoxb-demo-token",
            "SLACK_SIGNING_SECRET": "demo-signing-secret",
            "SLACK_APP_LEVEL_TOKEN": "xapp-demo-token",
            "SLACK_VERIFICATION_TOKEN": "demo-verification-token",
            
            "GOOGLE_CLIENT_ID": "demo-client-id",
            "GOOGLE_CLIENT_SECRET": "demo-client-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:8080/oauth/callback",
            
            "ASANA_ACCESS_TOKEN": "demo-asana-token",
            "ASANA_WORKSPACE_ID": "demo-workspace-id",
            "ASANA_WEBHOOK_SECRET": "demo-webhook-secret",
            
            # Email
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "sparkroboticai@gmail.com",
            "SMTP_PASSWORD": "demo-password",
            "SMTP_USE_TLS": "true",
            
            # Billing
            "STRIPE_SECRET_KEY": "sk_test_demo",
            "STRIPE_WEBHOOK_SECRET": "whsec_demo",
            
            # Webhooks
            "WEBHOOK_BASE_URL": "http://localhost:8080",
            
            # Celery
            "CELERY_BROKER_URL": "redis://localhost:6379/1",
            "CELERY_RESULT_BACKEND": "redis://localhost:6379/2",
            
            # Demo specific
            "DEMO_MODE": "true",
            "DEMO_USER_EMAIL": "demo@reflex.ai",
            "DEMO_USER_PASSWORD": "demo123"
        }
        
        # Write demo env file
        demo_env_path = self.project_root / ".env.demo"
        with open(demo_env_path, "w") as f:
            for key, value in demo_env.items():
                f.write(f"{key}={value}\n")
        
        print(f"✅ Demo environment file created: {demo_env_path}")
    
    def _setup_sample_data(self):
        """Setup sample data for demo."""
        print("📊 Setting up sample data...")
        
        # Sample users
        sample_users = [
            {
                "email": "demo@reflex.ai",
                "first_name": "Demo",
                "last_name": "User",
                "company_name": "Reflex Demo Corp",
                "role": "CEO",
                "plan_type": "professional"
            },
            {
                "email": "alice@demo.com",
                "first_name": "Alice",
                "last_name": "Johnson",
                "company_name": "Demo Startup",
                "role": "Product Manager",
                "plan_type": "starter"
            },
            {
                "email": "bob@demo.com",
                "first_name": "Bob",
                "last_name": "Smith",
                "company_name": "Demo Enterprise",
                "role": "CTO",
                "plan_type": "enterprise"
            }
        ]
        
        # Sample conversations
        sample_conversations = [
            {
                "user_id": "demo@reflex.ai",
                "platform": "slack",
                "title": "Project Planning Discussion",
                "messages": [
                    {"sender": "demo@reflex.ai", "content": "Can you help me plan the Q4 product launch?"},
                    {"sender": "ai", "content": "I'd be happy to help you plan the Q4 product launch! Let me gather some information about your current projects and create a comprehensive plan."}
                ]
            },
            {
                "user_id": "alice@demo.com",
                "platform": "email",
                "title": "Customer Support Request",
                "messages": [
                    {"sender": "alice@demo.com", "content": "I need help with my subscription billing"},
                    {"sender": "ai", "content": "I can help you with your subscription billing. Let me check your account and provide you with the information you need."}
                ]
            }
        ]
        
        # Sample workflows
        sample_workflows = [
            {
                "name": "Email Response Workflow",
                "description": "Automatically respond to common customer inquiries",
                "triggers": ["email_received"],
                "actions": ["analyze_email", "generate_response", "send_reply"]
            },
            {
                "name": "Meeting Scheduler",
                "description": "Schedule meetings based on availability",
                "triggers": ["calendar_request"],
                "actions": ["check_availability", "propose_times", "send_invites"]
            }
        ]
        
        # Save sample data
        sample_data = {
            "users": sample_users,
            "conversations": sample_conversations,
            "workflows": sample_workflows,
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        sample_data_path = self.data_dir / "sample_data.json"
        with open(sample_data_path, "w") as f:
            json.dump(sample_data, f, indent=2)
        
        print(f"✅ Sample data created: {sample_data_path}")
    
    def _create_demo_kb(self):
        """Create demo knowledge base with sample content."""
        print("🧠 Creating demo knowledge base...")
        
        # Sample knowledge base content
        kb_content = [
            {
                "title": "Company Overview",
                "content": "Reflex AI Assistant is a modern SaaS platform that provides AI-powered executive assistance for businesses of all sizes. Our mission is to make AI accessible to everyone.",
                "category": "company",
                "tags": ["company", "overview", "mission"]
            },
            {
                "title": "Product Features",
                "content": "Key features include: AI-powered conversations, Slack integration, Gmail automation, Asana workflows, knowledge base, analytics dashboard, and team collaboration.",
                "category": "product",
                "tags": ["features", "product", "capabilities"]
            },
            {
                "title": "Pricing Plans",
                "content": "We offer four pricing tiers: Free (50 conversations/month), Starter ($29/month, 500 conversations), Professional ($99/month, 2000 conversations), and Enterprise ($299/month, unlimited).",
                "category": "pricing",
                "tags": ["pricing", "plans", "subscription"]
            },
            {
                "title": "Getting Started",
                "content": "To get started: 1) Sign up for a free account, 2) Connect your tools (Slack, Gmail, Asana), 3) Start chatting with your AI assistant, 4) Explore features and upgrade as needed.",
                "category": "help",
                "tags": ["getting-started", "onboarding", "setup"]
            },
            {
                "title": "Support Information",
                "content": "For support, contact us at support@reflex.ai, visit our help center at help.reflex.ai, or join our community forum at community.reflex.ai.",
                "category": "support",
                "tags": ["support", "help", "contact"]
            }
        ]
        
        # Save knowledge base content
        kb_path = self.data_dir / "demo_knowledge_base.json"
        with open(kb_path, "w") as f:
            json.dump(kb_content, f, indent=2)
        
        print(f"✅ Demo knowledge base created: {kb_path}")
    
    def _setup_demo_integrations(self):
        """Setup demo integrations."""
        print("🔗 Setting up demo integrations...")
        
        # Demo integration configurations
        integrations = {
            "slack": {
                "workspace_name": "Reflex Demo Workspace",
                "channels": ["general", "ai-assistant", "random"],
                "webhook_url": "http://localhost:8080/webhooks/slack",
                "bot_name": "Reflex AI Assistant"
            },
            "gmail": {
                "email": "sparkroboticai@gmail.com",
                "labels": ["AI-Processed", "Important", "Follow-up"],
                "webhook_url": "http://localhost:8080/webhooks/gmail"
            },
            "asana": {
                "workspace_name": "Reflex Demo Projects",
                "projects": ["Product Launch", "Customer Support", "Team Management"],
                "webhook_url": "http://localhost:8080/webhooks/asana"
            }
        }
        
        # Save integration configs
        integrations_path = self.config_dir / "demo_integrations.json"
        with open(integrations_path, "w") as f:
            json.dump(integrations, f, indent=2)
        
        print(f"✅ Demo integrations configured: {integrations_path}")
    
    def _create_deployment_files(self, deployment_type: str):
        """Create deployment-specific files."""
        print(f"🚀 Creating {deployment_type} deployment files...")
        
        if deployment_type == "docker":
            self._create_docker_deployment()
        elif deployment_type == "kubernetes":
            self._create_k8s_deployment()
        elif deployment_type == "local":
            self._create_local_deployment()
    
    def _create_docker_deployment(self):
        """Create Docker deployment files."""
        # Demo docker-compose
        demo_compose = {
            "version": "3.8",
            "services": {
                "reflex-app": {
                    "build": ".",
                    "ports": ["8080:8080"],
                    "environment": ["DEMO_MODE=true"],
                    "env_file": [".env.demo"],
                    "depends_on": ["postgres", "redis"],
                    "volumes": ["./data:/app/data"]
                },
                "reflex-celery": {
                    "build": ".",
                    "command": "celery -A src.jobs.celery_app worker --loglevel=info",
                    "env_file": [".env.demo"],
                    "depends_on": ["postgres", "redis"]
                },
                "postgres": {
                    "image": "postgres:15",
                    "environment": {
                        "POSTGRES_DB": "reflex_demo",
                        "POSTGRES_USER": "reflex_user",
                        "POSTGRES_PASSWORD": "reflex_password"
                    },
                    "volumes": ["postgres_data:/var/lib/postgresql/data"]
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "ports": ["6379:6379"]
                },
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "ports": ["9090:9090"],
                    "volumes": ["./config/prometheus.yml:/etc/prometheus/prometheus.yml"]
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "ports": ["3000:3000"],
                    "environment": {
                        "GF_SECURITY_ADMIN_PASSWORD": "admin"
                    }
                }
            },
            "volumes": {
                "postgres_data": {}
            }
        }
        
        demo_compose_path = self.project_root / "docker-compose.demo.yml"
        with open(demo_compose_path, "w") as f:
            json.dump(demo_compose, f, indent=2)
        
        print(f"✅ Docker deployment files created: {demo_compose_path}")
    
    def _create_k8s_deployment(self):
        """Create Kubernetes deployment files."""
        # Demo namespace
        demo_namespace = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": "reflex-demo"
            }
        }
        
        demo_namespace_path = self.demos_dir / "k8s" / "namespace.yaml"
        demo_namespace_path.parent.mkdir(exist_ok=True)
        
        with open(demo_namespace_path, "w") as f:
            json.dump(demo_namespace, f, indent=2)
        
        print(f"✅ Kubernetes deployment files created: {demo_namespace_path}")
    
    def _create_local_deployment(self):
        """Create local deployment files."""
        # Local setup script
        local_setup = """#!/bin/bash
# Local Demo Setup Script

echo "🚀 Setting up Reflex AI Assistant locally..."

# Install dependencies
pip install -r requirements.txt

# Copy demo environment
cp .env.demo .env

# Initialize database
python scripts/manage_db.py init

# Seed demo data
python scripts/seed_demo_data.py

# Start services
echo "Starting Reflex AI Assistant..."
python -m src.app &
APP_PID=$!

echo "Starting Celery worker..."
celery -A src.jobs.celery_app worker --loglevel=info &
CELERY_PID=$!

echo "Starting Celery beat..."
celery -A src.jobs.celery_app beat --loglevel=info &
BEAT_PID=$!

echo "✅ Reflex AI Assistant is running!"
echo "🌐 Dashboard: http://localhost:8080"
echo "📊 API Docs: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $APP_PID $CELERY_PID $BEAT_PID; exit" INT
wait
"""
        
        local_setup_path = self.project_root / "scripts" / "start_demo_local.sh"
        with open(local_setup_path, "w") as f:
            f.write(local_setup)
        
        # Make executable
        os.chmod(local_setup_path, 0o755)
        
        print(f"✅ Local deployment files created: {local_setup_path}")
    
    def _setup_monitoring(self):
        """Setup monitoring configuration."""
        print("📊 Setting up monitoring...")
        
        # Prometheus config
        prometheus_config = {
            "global": {
                "scrape_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": "reflex-app",
                    "static_configs": [
                        {
                            "targets": ["reflex-app:8080"]
                        }
                    ]
                }
            ]
        }
        
        prometheus_path = self.config_dir / "prometheus.yml"
        with open(prometheus_path, "w") as f:
            json.dump(prometheus_config, f, indent=2)
        
        print(f"✅ Monitoring configuration created: {prometheus_path}")
    
    def _print_next_steps(self, deployment_type: str):
        """Print next steps for the user."""
        print("\n" + "="*60)
        print("🎉 Demo Environment Setup Complete!")
        print("="*60)
        
        if deployment_type == "docker":
            print("\n🚀 To start the demo:")
            print("1. docker-compose -f docker-compose.demo.yml up -d")
            print("2. Visit http://localhost:8080")
            print("3. Login with demo@reflex.ai / demo123")
        
        elif deployment_type == "kubernetes":
            print("\n🚀 To start the demo:")
            print("1. kubectl apply -f demos/k8s/")
            print("2. kubectl port-forward svc/reflex-app 8080:8080")
            print("3. Visit http://localhost:8080")
        
        elif deployment_type == "local":
            print("\n🚀 To start the demo:")
            print("1. ./scripts/start_demo_local.sh")
            print("2. Visit http://localhost:8080")
        
        print("\n📚 Demo Features:")
        print("• Pre-configured users and conversations")
        print("• Sample knowledge base")
        print("• Demo integrations (Slack, Gmail, Asana)")
        print("• Monitoring dashboard (Grafana)")
        print("• Analytics and usage tracking")
        
        print("\n🔧 Demo Credentials:")
        print("• Email: demo@reflex.ai")
        print("• Password: demo123")
        print("• Plan: Professional (2000 conversations/month)")
        
        print("\n📖 Documentation:")
        print("• User Guide: http://localhost:8080/docs")
        print("• API Reference: http://localhost:8080/docs")
        print("• Help Center: http://localhost:8080/help")
        
        print("\n" + "="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Reflex AI Assistant Starter Pack")
    parser.add_argument(
        "--deployment",
        choices=["docker", "kubernetes", "local"],
        default="docker",
        help="Deployment type (default: docker)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick setup with minimal configuration"
    )
    
    args = parser.parse_args()
    
    starter = StarterPack()
    starter.setup_demo_environment(args.deployment)


if __name__ == "__main__":
    main() 