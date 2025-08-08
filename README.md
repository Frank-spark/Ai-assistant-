# Reflex Executive Assistant — Development README

## Overview

Reflex Executive Assistant is a persistent, AI-driven agent for Spark Robotic. It maintains its own email, Slack, and Asana identity, acts on executive workflows, and uses a private knowledge base seeded from prior company context. This README provides architecture, setup, and operating procedures for developers.

## Capabilities

* Reads company context from a private knowledge base and responds in the established Spark style guide
* Monitors Gmail, Slack, and Asana events and converts them into actions
* Drafts emails, Slack messages, and Asana tasks with optional human-in-the-loop approval
* Generates meeting notes, agendas, follow-ups, and status summaries
* Enforces organizational constraints including excluded markets for Spark business strategy

## Architecture

* API service: FastAPI
* Orchestration: LangChain
* Retrieval: Vector database (Pinecone, Weaviate, or Milvus)
* Persistence: Postgres
* Message bus: Redis (queues for event handling)
* Integrations

  * Gmail API via Google Workspace
  * Slack Events API and Web API
  * Asana REST API
* Authentication and secrets: Vault or Doppler
* Telemetry: OpenTelemetry, Prometheus, and structured JSON logs

## Identity and Accounts

Create a dedicated identity for the assistant.

* Email: [assistant@sparkrobotic.com](mailto:assistant@sparkrobotic.com) (Google Workspace)
* Slack: invite the email as a user and assign required channels
* Asana: invite the email to the organization and projects with appropriate permissions

## Permissions and Scopes

Gmail

* Gmail API scopes: gmail.readonly, gmail.send, gmail.modify
* Directory scope if needed for user lookups: admin.directory.user.readonly

Slack

* Bot scopes: app\_mentions\:read, channels\:history, chat\:write, im\:history, im\:write, channels\:read, users\:read, files\:write
* Events: app\_mention, message.channels, message.im, reaction\_added

Asana

* personal access token or OAuth app
* scopes: default Asana API with project, section, task, user, and webhook access

## Tech Stack

* Python 3.11
* FastAPI for HTTP endpoints and webhooks
* LangChain for RAG and tool routing
* Pydantic for data models
* SQLAlchemy for Postgres access
* Celery or RQ for background jobs on Redis
* pytest for tests
* ruff and black for linting and formatting

## Repository Structure

```
reflex-executive-assistant/
  README.md
  pyproject.toml
  src/
    app.py                   # FastAPI app and router assembly
    config.py                # env parsing and settings
    auth/
      google_oauth.py
      slack_oauth.py
      asana_oauth.py
    integrations/
      gmail_client.py
      slack_client.py
      asana_client.py
      webhooks/
        gmail_webhook.py
        slack_events.py
        asana_webhook.py
    kb/
      loader.py              # seed and update knowledge base
      retriever.py           # vector DB retriever
      schema.py              # chunk, doc, and metadata schemas
    ai/
      prompts.py
      chain.py               # RAG pipeline and tool use
      policies.py            # guardrails and exclusions
      tools/
        email_tools.py
        slack_tools.py
        asana_tools.py
        calendar_tools.py
    workflows/
      router.py              # event to workflow routing
      email_triage.py
      meeting_notes.py
      followups.py
      asana_sync.py
      status_reports.py
    storage/
      db.py
      models.py
      migrations/
    jobs/
      queue.py               # Celery or RQ setup
      tasks.py               # background task definitions
    logging/
      setup.py
  deployments/
    docker/
      Dockerfile
      docker-compose.yml
    k8s/
      deployment.yaml
      service.yaml
  scripts/
    seed_kb.py
    create_webhooks.py
    dev_tunnel.sh
  tests/
    unit/
    integration/
  .env.example
```

## Environment Configuration

Copy .env.example to .env and fill values.

```
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

1. Install dependencies

   ```
   uv sync
   ```

   or

   ```
   pip install -e .
   ```
2. Run Postgres and Redis locally

   ```
   docker compose -f deployments/docker/docker-compose.yml up -d postgres redis
   ```
3. Apply database migrations

   ```
   alembic upgrade head
   ```
4. Start the API

   ```
   uvicorn src.app:app --reload --port 8080
   ```
5. Start the job worker

   ```
   python -m src.jobs.queue
   ```

## Knowledge Base Seeding

1. Compile the Spark context into markdown files under data/kb

   * model\_set\_context.md
   * assistant\_preferences.md
   * notable\_topics.md
   * operating\_constraints.md
2. Chunk and index

   ```
   python scripts/seed_kb.py --path data/kb --index reflex-kb-v1
   ```
3. Verify retrieval

   ```
   pytest tests/integration/test_retriever.py
   ```

## Prompting and Guardrails

* The assistant must write in Spark’s preferred style
* No bold text or emojis in outputs
* Exclude therapeutic, wellness, and medical markets in business suggestions
* Add explicit disclaimers on authority for financial or legal commitments
* All high-impact actions require human approval

Prompts are defined in src/ai/prompts.py and policies in src/ai/policies.py.

## Event Routing

Event router maps source events to workflows in src/workflows/router.py.

* Gmail new message in Exec inbox → email\_triage.create\_draft or meeting\_notes.invite\_prep
* Slack mention or DM → intent detection then slack\_tools.respond or asana\_sync.create\_task
* Asana due or overdue → followups.remind\_owner and optional Slack DM

## Example Chains

RAG assistant chain with tools for email, Slack, and Asana.

```python
# src/ai/chain.py
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from .prompts import SYSTEM_PROMPT
from ..kb.retriever import get_retriever
from .tools.email_tools import send_draft_email
from .tools.slack_tools import post_message
from .tools.asana_tools import create_task

def build_chain(llm):
    retriever = get_retriever()
    def tool_router(intent, data):
        if intent == "email_draft":
            return send_draft_email(data)
        if intent == "slack_post":
            return post_message(data)
        if intent == "asana_task":
            return create_task(data)
        return {"status": "no-op"}

    chain = RunnableParallel({
        "context": retriever,
        "input": RunnablePassthrough()
    }).assign(
        answer=lambda x: llm.invoke({
            "system": SYSTEM_PROMPT,
            "context": x["context"],
            "input": x["input"]
        })
    )
    return chain, tool_router
```

## Webhooks

Expose these endpoints in FastAPI.

* POST /webhooks/slack/events
* POST /webhooks/gmail/notifications
* POST /webhooks/asana/events
* GET /healthz

Register webhooks with scripts/create\_webhooks.py after deployment.

## Human-in-the-Loop Controls

* Approval queue in Postgres
* Slack interactive messages to approve or reject drafts
* Default safe mode on for new deployments
* Policy toggles per channel or project

## Example Workflows

Email triage

1. Gmail push notification received
2. Fetch full thread
3. Summarize and propose next actions
4. Draft email and place into approval queue
5. On approval, send via Gmail API and log

Meeting notes

1. Calendar invite or transcript available
2. Summarize agenda and attendees
3. Create Asana placeholders for decisions, action items, and owners
4. Send Slack recap to channel and email to attendees

Asana hygiene

1. Nightly scan for overdue tasks owned by Spark
2. DM owners in Slack with context and quick action buttons
3. Escalate to a summarized report for leadership weekly

## Coding Standards

* Use descriptive names for variables and functions
* Docstrings for every public function and class
* Type hints everywhere
* Structured logging with request and correlation IDs
* Unit tests for pure logic, integration tests for API and tools

## Logging and Monitoring

* JSON logs with service, route, user, and correlation\_id fields
* OpenTelemetry tracing for request span and tool invocations
* Prometheus metrics for queue depth, webhook latency, error rates
* Alerting for persistent failures and webhook retries

## Security

* Principle of least privilege on all scopes
* Secrets stored in Vault or Doppler, not in env files for prod
* Service account for Gmail where appropriate
* Regular token rotation
* PII minimization in logs
* Policy enforcement for excluded markets

## Testing

* pytest unit tests with coverage
* Record-replay cassettes for API calls using vcrpy
* Integration tests for webhooks and tool operations
* Load tests for event spikes using Locust or k6

## CI/CD

* Lint, type-check, test on PR
* Build container image with SBOM
* Push to registry on main
* Staged deploy to dev, staging, prod
* Run database migrations on startup gate

## Deployment

Local docker compose

```
docker compose -f deployments/docker/docker-compose.yml up -d
```

Kubernetes

* Apply deployments/k8s manifests
* Configure ingress, TLS, and external webhooks
* Use HorizontalPodAutoscaler for worker scaling

## Runbook

* Rotate Asana, Slack, Google tokens monthly
* Reindex KB when new company docs are added
* Review approval queue daily
* Weekly status report generation to leadership channel and email
* Monthly audit of logs and access

## Roadmap

* Calendar integration for auto-scheduling and agenda preparation
* CRM integration for account health summaries
* Multi-agent specialization for research vs. execution
* Fine-tuning or adapters for domain phrasing
* On-prem model hosting for sensitive workloads

## Notes for Spark Constraints

Do not generate strategic recommendations for therapeutic, wellness, or medical product markets when acting on behalf of Spark Robotic.

## Quick Start

1. Create [assistant@sparkrobotic.com](mailto:assistant@sparkrobotic.com) in Google Workspace, Slack, and Asana
2. Fill .env and provision secrets
3. Run Postgres and Redis
4. Seed the KB
5. Start API and worker
6. Register webhooks
7. Enable safe mode and begin approvals
