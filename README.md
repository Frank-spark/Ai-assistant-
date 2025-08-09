# Reflex Executive Assistant — Development README

## Overview

Reflex Executive Assistant is a persistent, AI-driven agent for Spark Robotic. It maintains its own email, Slack, and Asana identity, acts on executive workflows, and uses a private knowledge base seeded from prior company context. This README provides architecture, setup, and operating procedures for developers.

## Current Development Status

**COMPLETED COMPONENTS:**
- **Authentication System**: JWT-based auth with FastAPI dependencies
- **Webhook Infrastructure**: Slack, Gmail, and Asana webhook handlers
- **Workflow Router**: Event routing and workflow orchestration
- **AI Chain**: Core LangChain integration with OpenAI and tool orchestration
- **Knowledge Base**: Vector database integration (Pinecone implemented, Weaviate/Milvus placeholders)
- **Background Job System**: Complete Celery infrastructure with Redis
- **Task Modules**: Email, Slack, Asana, and Workflow background processing
- **Database Models**: Core data models for all integrations

**IN PROGRESS:**
- AI Tools Implementation (BaseTool classes with TODO placeholders)
- JWT Token Validation (authentication dependencies)
- Database Migrations and Setup

**PENDING:**
- Docker Configuration
- Knowledge Base Seeding Scripts
- Webhook Registration Scripts
- Testing Infrastructure
- Deployment Manifests

## Capabilities

* Reads company context from a private knowledge base and responds in the established Spark style guide
* Monitors Gmail, Slack, and Asana events and converts them into actions
* Drafts emails, Slack messages, and Asana tasks with optional human-in-the-loop approval
* Generates meeting notes, agendas, follow-ups, and status summaries
* Enforces organizational constraints including excluded markets for Spark business strategy

## Architecture

* **API Service**: FastAPI with JWT authentication
* **Orchestration**: LangChain with OpenAI GPT-4 integration
* **Retrieval**: Vector database (Pinecone implemented, Weaviate/Milvus planned)
* **Persistence**: PostgreSQL with SQLAlchemy ORM
* **Message Bus**: Redis with Celery for background job processing
* **Integrations**:
  * Gmail API via Google Workspace
  * Slack Events API and Web API
  * Asana REST API
* **Authentication**: JWT tokens with FastAPI dependencies
* **Background Processing**: Celery with Redis backend and Celery Beat scheduler
* **Telemetry**: Structured JSON logging with correlation IDs

## Identity and Accounts

Create a dedicated identity for the assistant.

* Email: [sparkroboticai@gmail.com](mailto:sparkroboticai@gmail.com) (Google Workspace)
* Slack: invite the email as a user and assign required channels
* Asana: invite the email to the organization and projects with appropriate permissions

## Permissions and Scopes

### Gmail
* Gmail API scopes: gmail.readonly, gmail.send, gmail.modify
* Directory scope if needed for user lookups: admin.directory.user.readonly

### Slack
* Bot scopes: app_mentions:read, channels:history, chat:write, im:history, im:write, channels:read, users:read, files:write
* Events: app_mention, message.channels, message.im, reaction_added

### Asana
* Personal access token or OAuth app
* Scopes: default Asana API with project, section, task, user, and webhook access

## Tech Stack

* **Python 3.11+**
* **FastAPI** for HTTP endpoints and webhooks
* **LangChain** for RAG and tool routing
* **OpenAI GPT-4** for AI processing
* **Pydantic** for data models
* **SQLAlchemy** for PostgreSQL access
* **Celery** for background jobs on Redis
* **Redis** for message broker and result backend
* **PostgreSQL** for persistent storage
* **Pinecone** for vector database (primary)
* **pytest** for tests
* **ruff** and **black** for linting and formatting

## Repository Structure

```
reflex-executive-assistant/
├── README.md
├── pyproject.toml
├── env.example
├── src/
│   ├── __init__.py
│   ├── app.py                   # FastAPI app and router assembly
│   ├── config.py                # Environment parsing and settings
│   ├── auth/
│   │   ├── __init__.py
│   │   └── dependencies.py      # JWT authentication dependencies
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── gmail_client.py      # Gmail API client
│   │   ├── slack_client.py      # Slack API client
│   │   ├── asana_client.py      # Asana API client
│   │   └── webhooks/
│   │       ├── __init__.py
│   │       ├── gmail.py         # Gmail webhook handler
│   │       ├── slack.py         # Slack webhook handler
│   │       └── asana.py         # Asana webhook handler
│   ├── kb/
│   │   ├── __init__.py
│   │   └── retriever.py         # Vector database retriever
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── prompts.py           # AI prompts and system messages
│   │   ├── chain.py             # LangChain pipeline and tool orchestration
│   │   └── tools/               # AI tool implementations
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── engine.py            # Workflow execution engine
│   │   └── router.py            # Event routing and workflow orchestration
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py                # Database connection and session management
│   │   ├── models.py            # SQLAlchemy data models
│   │   └── migrations/          # Database migrations
│   ├── jobs/
│   │   ├── __init__.py          # Jobs package initialization
│   │   ├── celery_app.py        # Celery application configuration
│   │   └── tasks/
│   │       ├── __init__.py      # Tasks package initialization
│   │       ├── email_tasks.py   # Email background processing
│   │       ├── slack_tasks.py   # Slack background processing
│   │       ├── asana_tasks.py   # Asana background processing
│   │       ├── workflow_tasks.py # Workflow orchestration tasks
│   │       └── maintenance_tasks.py # System maintenance tasks
│   └── logging/
│       ├── __init__.py
│       └── setup.py             # Logging configuration
├── deployments/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── k8s/
│       ├── deployment.yaml
│       └── service.yaml
├── scripts/
│   ├── seed_kb.py               # Knowledge base seeding
│   └── create_webhooks.py       # Webhook registration
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
└── data/
    └── kb/                      # Knowledge base documents
```

## Environment Configuration

Copy `env.example` to `.env` and fill values.

```bash
APP_ENV=dev
PORT=8080

# LLM
OPENAI_API_KEY=your_key
MODEL_NAME=gpt-4o-mini

# Vector DB
VECTOR_DB_PROVIDER=pinecone
PINECONE_API_KEY=your_key
PINECONE_ENV=us-east-1
PINECONE_INDEX=reflex-kb-v1

# Postgres
POSTGRES_URL=postgresql+psycopg2://user:pass@localhost:5432/reflex

# Redis
REDIS_URL=redis://localhost:6379/0

# Gmail
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your.domain.com/oauth/google/callback
GOOGLE_SERVICE_ACCOUNT_JSON_BASE64=...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_LEVEL_TOKEN=xapp-...

# Asana
ASANA_ACCESS_TOKEN=...
ASANA_WEBHOOK_SECRET=...

# Guardrails and policy
EXCLUDED_MARKETS=therapeutic,wellness,medical
STYLE_NO_BOLD=true
STYLE_NO_EMOJI=true
```

## Local Development Setup

1. **Install dependencies**
   ```bash
   uv sync
   ```
   or
   ```bash
   pip install -e .
   ```

2. **Run PostgreSQL and Redis locally**
   ```bash
   docker compose -f deployments/docker/docker-compose.yml up -d postgres redis
   ```

3. **Apply database migrations**
   ```bash
   alembic upgrade head
   ```

4. **Start the API**
   ```bash
   uvicorn src.app:app --reload --port 8080
   ```

5. **Start the Celery worker**
   ```bash
   celery -A src.jobs.celery_app worker --loglevel=info
   ```

6. **Start the Celery Beat scheduler**
   ```bash
   celery -A src.jobs.celery_app beat --loglevel=info
   ```

## Background Job System

The system uses **Celery** with **Redis** for background processing:

### **Job Queues:**
- **email**: Email processing and synchronization
- **slack**: Slack message processing and monitoring
- **asana**: Asana project and task management
- **workflow**: Workflow orchestration and execution
- **maintenance**: System cleanup and health checks

### **Scheduled Tasks:**
- **Email Sync**: Every 10 minutes
- **Slack Sync**: Every 15 minutes
- **Asana Sync**: Every 20 minutes
- **Workflow Monitoring**: Every 5 minutes
- **Performance Analysis**: Daily at 2 AM
- **Data Cleanup**: Weekly on Sundays

### **Key Background Tasks:**
- **Email Processing**: AI-powered email analysis and drafting
- **Slack Monitoring**: Channel monitoring and intelligent message processing
- **Asana Management**: Project health analysis and deadline monitoring
- **Workflow Orchestration**: Execution monitoring and retry mechanisms
- **System Maintenance**: Performance analysis and routing optimization

## Knowledge Base Seeding

1. **Compile the Spark context into markdown files under `data/kb`**
   * `model_set_context.md`
   * `assistant_preferences.md`
   * `notable_topics.md`
   * `operating_constraints.md`

2. **Chunk and index**
   ```bash
   python scripts/seed_kb.py --path data/kb --index reflex-kb-v1
   ```

3. **Verify retrieval**
   ```bash
   pytest tests/integration/test_retriever.py
   ```

## AI Chain and Tools

The AI system is built on **LangChain** with comprehensive tool integration:

### **Core Components:**
- **ReflexAIChain**: Main AI processing pipeline
- **OpenAI Integration**: GPT-4 for chat and embeddings
- **Tool Orchestration**: 20+ specialized tools for different operations
- **Memory Management**: Conversation buffer with windowing
- **Function Calling**: OpenAI function calling for structured outputs

### **Tool Categories:**
- **Email Tools**: Drafting, sending, and analysis
- **Slack Tools**: Messaging, channel management, and monitoring
- **Asana Tools**: Task creation, project management, and updates
- **Calendar Tools**: Meeting scheduling and agenda preparation
- **Knowledge Base Tools**: Document retrieval and context building
- **Utility Tools**: Data processing and system operations

### **Intelligence Features:**
- **Multi-Query Retrieval**: Enhanced document retrieval using multiple queries
- **Context-Aware Processing**: Company-specific knowledge integration
- **Smart Routing**: Automatic tool selection based on content analysis
- **Conversation Memory**: Persistent context across interactions

## Event Routing and Workflows

The **Workflow Router** (`src/workflows/router.py`) handles event routing:

### **Event Types:**
- **Slack Events**: Mentions, messages, reactions
- **Email Events**: Urgent emails, meeting emails, task emails
- **Asana Events**: Task updates, project changes, story updates

### **Workflow Types:**
- **slack_mention**: Direct mentions and DMs
- **slack_message**: Channel message processing
- **slack_reaction**: Reaction-based workflows
- **urgent_email**: High-priority email handling
- **meeting_email**: Calendar and meeting coordination
- **task_email**: Task-related email processing
- **asana_task**: Task management workflows
- **project_event**: Project-level changes
- **story_event**: Comment and update workflows

### **Workflow Execution:**
- **Status Tracking**: started → processing → completed/failed
- **Retry Mechanism**: Exponential backoff for failed workflows
- **Timeout Handling**: 30-minute timeout for stuck workflows
- **Performance Monitoring**: Success rates and processing times
- **AI Integration**: Full AI processing for all workflow types

## Webhooks

Expose these endpoints in FastAPI:

* `POST /webhooks/slack/events` - Slack event processing
* `POST /webhooks/gmail/notifications` - Gmail push notifications
* `POST /webhooks/asana/events` - Asana webhook events
* `GET /healthz` - Health check endpoint

Register webhooks with `scripts/create_webhooks.py` after deployment.

## Human-in-the-Loop Controls

* **Approval Queue**: PostgreSQL-based approval system
* **Slack Interactive Messages**: Approve or reject drafts via Slack
* **Safe Mode**: Default safe mode for new deployments
* **Policy Toggles**: Per-channel or project policy controls
* **Workflow Approval**: Human approval for high-impact actions

## Example Workflows

### **Email Triage**
1. Gmail push notification received
2. Fetch full thread and analyze content
3. Summarize and propose next actions
4. Draft email and place into approval queue
5. On approval, send via Gmail API and log

### **Meeting Notes**
1. Calendar invite or transcript available
2. Summarize agenda and attendees
3. Create Asana placeholders for decisions, action items, and owners
4. Send Slack recap to channel and email to attendees

### **Asana Hygiene**
1. Nightly scan for overdue tasks owned by Spark
2. DM owners in Slack with context and quick action buttons
3. Escalate to a summarized report for leadership weekly

### **Slack Intelligence**
1. Monitor channels for important keywords and mentions
2. Process messages with AI for intent detection
3. Route to appropriate workflows (task creation, meeting scheduling, etc.)
4. Provide contextual responses and follow-up actions

## Coding Standards

* **Descriptive Names**: Clear variable and function naming
* **Comprehensive Docstrings**: Every public function and class documented
* **Type Hints**: Full type annotation throughout the codebase
* **Structured Logging**: Request and correlation ID tracking
* **Error Handling**: Comprehensive exception handling and logging
* **Testing**: Unit tests for pure logic, integration tests for API and tools

## Logging and Monitoring

* **JSON Logs**: Structured logging with service, route, user, and correlation_id fields
* **Correlation IDs**: Request tracing across all components
* **Performance Metrics**: Queue depth, webhook latency, error rates
* **Health Checks**: Comprehensive system health monitoring
* **Alerting**: Persistent failures and webhook retry notifications

## Security

* **Principle of Least Privilege**: Minimal scopes on all API integrations
* **JWT Authentication**: Secure token-based authentication
* **Secrets Management**: Environment-based configuration (Vault/Doppler for production)
* **Service Accounts**: Gmail service account where appropriate
* **Token Rotation**: Regular token rotation and monitoring
* **PII Minimization**: Minimal personal data in logs
* **Policy Enforcement**: Excluded markets and business constraints

## Testing

* **pytest**: Unit tests with coverage requirements
* **Integration Tests**: Webhook and tool operation testing
* **API Testing**: FastAPI endpoint validation
* **Background Job Testing**: Celery task execution testing
* **Load Testing**: Event spike handling with Locust or k6

## CI/CD

* **Code Quality**: Lint, type-check, and test on PR
* **Container Builds**: Docker image building with SBOM
* **Registry Management**: Automated pushes to container registry
* **Staged Deployment**: Dev → staging → production pipeline
* **Database Migrations**: Startup gate migration execution

## Deployment

### **Local Docker Compose**
```bash
docker compose -f deployments/docker/docker-compose.yml up -d
```

### **Kubernetes**
* Apply `deployments/k8s` manifests
* Configure ingress, TLS, and external webhooks
* Use HorizontalPodAutoscaler for worker scaling
* Configure resource limits and health checks

## Runbook

* **Token Rotation**: Monthly rotation of Asana, Slack, and Google tokens
* **Knowledge Base Updates**: Reindex when new company documents are added
* **Approval Queue Review**: Daily review of pending approvals
* **Status Reports**: Weekly status report generation to leadership
* **Performance Monitoring**: Monthly audit of logs, performance, and access
* **System Health**: Regular health checks and maintenance tasks

## Roadmap

### **Phase 1 (Current)**
* COMPLETED: Core infrastructure and background job system
* COMPLETED: AI chain and tool orchestration
* COMPLETED: Webhook handling and workflow routing
* IN PROGRESS: AI tools implementation and testing
* PENDING: Docker and deployment configuration

### **Phase 2 (Next)**
* Calendar integration for auto-scheduling and agenda preparation
* CRM integration for account health summaries
* Advanced workflow orchestration and decision trees
* Performance optimization and scaling improvements

### **Phase 3 (Future)**
* Multi-agent specialization for research vs. execution
* Fine-tuning or adapters for domain-specific phrasing
* On-prem model hosting for sensitive workloads
* Advanced analytics and business intelligence

## Notes for Spark Constraints

**Do not generate strategic recommendations for therapeutic, wellness, or medical product markets when acting on behalf of Spark Robotic.**

## Quick Start

1. **Create assistant accounts** in Google Workspace, Slack, and Asana
2. **Configure environment** by copying `.env.example` to `.env`
3. **Start infrastructure** with PostgreSQL and Redis
4. **Seed the knowledge base** with company context
5. **Start the system**:
   ```bash
   # Terminal 1: API
   uvicorn src.app:app --reload --port 8080
   
   # Terminal 2: Celery Worker
   celery -A src.jobs.celery_app worker --loglevel=info
   
   # Terminal 3: Celery Beat
   celery -A src.jobs.celery_app beat --loglevel=info
   ```
6. **Register webhooks** with external services
7. **Enable safe mode** and begin human approval workflow

## Development Commands

### **Start Development Environment**
```bash
# Install dependencies
uv sync

# Start databases
docker compose -f deployments/docker/docker-compose.yml up -d postgres redis

# Run migrations
alembic upgrade head

# Start all services
./scripts/dev_start.sh
```

### **Run Tests**
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=src tests/
```

### **Code Quality**
```bash
# Linting
ruff check src/

# Formatting
black src/

# Type checking
mypy src/
```

## Support and Contributing

* **Issues**: Report bugs and feature requests via GitHub issues
* **Discussions**: Use GitHub discussions for questions and ideas
* **Contributing**: Follow the coding standards and testing requirements
* **Documentation**: Keep this README updated with new features

---

**Last Updated**: December 2024  
**Development Status**: Core Infrastructure Complete, AI Tools Implementation In Progress  
**Next Milestone**: Complete AI Tools and Begin Testing Phase
