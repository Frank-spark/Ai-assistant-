#!/bin/bash

# Reflex AI Assistant - One-Click Demo Startup Script
# This script sets up a complete demo environment in 5 minutes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Demo configuration
DEMO_NAME="reflex-demo"
DEMO_PORT="8080"
DEMO_COMPOSE_FILE="docker-compose.demo.yml"

echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                Reflex AI Assistant Demo                      ║"
echo "║                    One-Click Startup                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print status messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Prerequisites check passed"

# Check if demo is already running
if docker-compose -f $DEMO_COMPOSE_FILE ps | grep -q "Up"; then
    print_warning "Demo environment is already running!"
    echo -e "${CYAN}Demo URL: http://localhost:$DEMO_PORT${NC}"
    echo -e "${CYAN}Grafana: http://localhost:3000 (admin/admin)${NC}"
    echo -e "${CYAN}Prometheus: http://localhost:9090${NC}"
    exit 0
fi

# Create necessary directories
print_status "Creating demo directories..."
mkdir -p data/kb
mkdir -p data/logs
mkdir -p mocks
mkdir -p monitoring

print_success "Directories created"

# Create mock API configurations
print_status "Setting up mock APIs..."

# Mock Slack API
cat > mocks/slack.json << 'EOF'
[
  {
    "httpRequest": {
      "method": "POST",
      "path": "/api/chat.postMessage"
    },
    "httpResponse": {
      "statusCode": 200,
      "body": {
        "ok": true,
        "channel": "C123456",
        "ts": "1234567890.123456",
        "message": {
          "text": "Demo message sent successfully"
        }
      }
    }
  },
  {
    "httpRequest": {
      "method": "GET",
      "path": "/api/conversations.list"
    },
    "httpResponse": {
      "statusCode": 200,
      "body": {
        "ok": true,
        "channels": [
          {
            "id": "C123456",
            "name": "general",
            "is_private": false
          },
          {
            "id": "C789012",
            "name": "sales",
            "is_private": false
          }
        ]
      }
    }
  }
]
EOF

# Mock Gmail API
cat > mocks/gmail.json << 'EOF'
[
  {
    "httpRequest": {
      "method": "GET",
      "path": "/gmail/v1/users/me/messages"
    },
    "httpResponse": {
      "statusCode": 200,
      "body": {
        "messages": [
          {
            "id": "msg-1",
            "threadId": "thread-1"
          },
          {
            "id": "msg-2",
            "threadId": "thread-2"
          }
        ]
      }
    }
  },
  {
    "httpRequest": {
      "method": "POST",
      "path": "/gmail/v1/users/me/messages/send"
    },
    "httpResponse": {
      "statusCode": 200,
      "body": {
        "id": "msg-sent-1",
        "threadId": "thread-1"
      }
    }
  }
]
EOF

# Mock Asana API
cat > mocks/asana.json << 'EOF'
[
  {
    "httpRequest": {
      "method": "GET",
      "path": "/api/1.0/projects"
    },
    "httpResponse": {
      "statusCode": 200,
      "body": {
        "data": [
          {
            "id": "project-123",
            "name": "Series A Growth Plan",
            "description": "Strategic initiatives to scale the company"
          },
          {
            "id": "project-456",
            "name": "Enterprise Corp Deal",
            "description": "Sales process and implementation"
          }
        ]
      }
    }
  },
  {
    "httpRequest": {
      "method": "POST",
      "path": "/api/1.0/tasks"
    },
    "httpResponse": {
      "statusCode": 200,
      "body": {
        "data": {
          "id": "task-123",
          "name": "Demo Task",
          "description": "Task created by Reflex AI"
        }
      }
    }
  }
]
EOF

print_success "Mock APIs configured"

# Create monitoring configuration
print_status "Setting up monitoring..."

# Prometheus configuration
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'reflex-app'
    static_configs:
      - targets: ['app:8080']
    metrics_path: '/metrics'

  - job_name: 'reflex-celery'
    static_configs:
      - targets: ['celery:8080']
    metrics_path: '/metrics'
EOF

# Create Grafana datasource
mkdir -p monitoring/grafana/datasources
cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Create Grafana dashboard
mkdir -p monitoring/grafana/dashboards
cat > monitoring/grafana/dashboards/reflex-demo.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Reflex AI Assistant Demo",
    "tags": ["reflex", "demo"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Active Users",
        "type": "stat",
        "targets": [
          {
            "expr": "reflex_active_users",
            "legendFormat": "Users"
          }
        ]
      },
      {
        "id": 2,
        "title": "Conversations per Hour",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(reflex_conversations_total[1h])",
            "legendFormat": "Conversations/hour"
          }
        ]
      }
    ]
  }
}
EOF

print_success "Monitoring configured"

# Set up environment variables
print_status "Setting up environment variables..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# Demo Environment Variables
APP_ENV=demo
DEBUG=true
LOG_LEVEL=INFO

# AI Models (use your own keys for full functionality)
OPENAI_API_KEY=sk-demo-key-for-demo-purposes-only
ANTHROPIC_API_KEY=sk-ant-demo-key-for-demo-purposes-only

# Database
POSTGRES_URL=postgresql://reflex_user:reflex_password@postgres:5432/reflex_demo
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=demo-secret-key-32-chars-minimum-for-demo
JWT_SECRET=demo-jwt-secret-32-chars-minimum-for-demo

# Webhook Base URL
WEBHOOK_BASE_URL=http://localhost:8080

# Email Configuration
SMTP_USERNAME=sparkroboticai@gmail.com
SMTP_PASSWORD=demo-password

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Demo Integrations (Mock)
SLACK_BOT_TOKEN=xoxb-demo-token
SLACK_SIGNING_SECRET=demo-signing-secret
SLACK_APP_LEVEL_TOKEN=xapp-demo-token
SLACK_VERIFICATION_TOKEN=demo-verification-token

GMAIL_CLIENT_ID=demo-gmail-client-id
GMAIL_CLIENT_SECRET=demo-gmail-client-secret
GMAIL_REDIRECT_URI=http://localhost:8080/oauth/callback

ASANA_ACCESS_TOKEN=demo-asana-token
ASANA_WORKSPACE_ID=demo-workspace-id
ASANA_WEBHOOK_SECRET=demo-webhook-secret

STRIPE_SECRET_KEY=demo-stripe-key
STRIPE_WEBHOOK_SECRET=demo-stripe-webhook
EOF
    print_success "Environment file created"
else
    print_warning "Environment file already exists"
fi

# Start the demo environment
print_status "Starting demo environment..."

# Pull latest images
print_status "Pulling Docker images..."
docker-compose -f $DEMO_COMPOSE_FILE pull

# Start services
print_status "Starting services..."
docker-compose -f $DEMO_COMPOSE_FILE up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."

# Wait for PostgreSQL
print_status "Waiting for PostgreSQL..."
until docker-compose -f $DEMO_COMPOSE_FILE exec -T postgres pg_isready -U reflex_user -d reflex_demo; do
    sleep 2
done
print_success "PostgreSQL is ready"

# Wait for Redis
print_status "Waiting for Redis..."
until docker-compose -f $DEMO_COMPOSE_FILE exec -T redis redis-cli ping; do
    sleep 2
done
print_success "Redis is ready"

# Wait for main application
print_status "Waiting for application..."
until curl -f http://localhost:$DEMO_PORT/health >/dev/null 2>&1; do
    sleep 5
done
print_success "Application is ready"

# Run demo seeder
print_status "Seeding demo data..."
docker-compose -f $DEMO_COMPOSE_FILE run --rm demo-seeder

print_success "Demo environment is ready!"

# Display demo information
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Demo Environment Ready!                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}🎯 Demo URLs:${NC}"
echo -e "   Main Application: ${BLUE}http://localhost:$DEMO_PORT${NC}"
echo -e "   Demo Dashboard:   ${BLUE}http://localhost:$DEMO_PORT/demo${NC}"
echo -e "   Voice Demo:       ${BLUE}http://localhost:$DEMO_PORT/demo/voice${NC}"
echo -e "   Team Demo:        ${BLUE}http://localhost:$DEMO_PORT/demo/team${NC}"
echo -e "   Workflows Demo:   ${BLUE}http://localhost:$DEMO_PORT/demo/workflows${NC}"

echo -e "${CYAN}📊 Monitoring:${NC}"
echo -e "   Grafana:          ${BLUE}http://localhost:3000${NC} (admin/admin)"
echo -e "   Prometheus:       ${BLUE}http://localhost:9090${NC}"

echo -e "${CYAN}🔑 Demo Credentials:${NC}"
echo -e "   CEO:              ${YELLOW}sarah@techflow.com${NC}"
echo -e "   CTO:              ${YELLOW}mike@techflow.com${NC}"
echo -e "   Marketing:        ${YELLOW}jen@techflow.com${NC}"
echo -e "   Sales:            ${YELLOW}alex@techflow.com${NC}"

echo -e "${CYAN}📋 Demo Features:${NC}"
echo -e "   ✅ Voice conversations with AI assistant"
echo -e "   ✅ Strategic dashboard with KPIs"
echo -e "   ✅ Team alignment and goal tracking"
echo -e "   ✅ Workflow automation examples"
echo -e "   ✅ Email triage and response"
echo -e "   ✅ Task creation and management"
echo -e "   ✅ Meeting scheduling automation"

echo -e "${CYAN}⚡ Quick Start:${NC}"
echo -e "   1. Visit ${BLUE}http://localhost:$DEMO_PORT/demo${NC}"
echo -e "   2. Try the voice demo: ${BLUE}http://localhost:$DEMO_PORT/demo/voice${NC}"
echo -e "   3. Explore the dashboard: ${BLUE}http://localhost:$DEMO_PORT/demo/dashboard${NC}"
echo -e "   4. Check team alignment: ${BLUE}http://localhost:$DEMO_PORT/demo/team${NC}"

echo -e "${YELLOW}"
echo "💡 Tip: Use 'docker-compose -f $DEMO_COMPOSE_FILE logs -f' to view logs"
echo "💡 Tip: Use 'docker-compose -f $DEMO_COMPOSE_FILE down' to stop the demo"
echo -e "${NC}"

# Show running services
echo -e "${CYAN}🔄 Running Services:${NC}"
docker-compose -f $DEMO_COMPOSE_FILE ps

print_success "Demo environment started successfully!"
print_success "Your 5-minute demo is ready to go! 🚀" 