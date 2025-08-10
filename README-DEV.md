# Reflex Executive AI Assistant - Developer Documentation

> **Technical documentation for developers working on the Reflex Executive AI Assistant platform.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-20+-blue.svg)](https://docker.com)

## **Table of Contents**

- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Core Components](#core-components)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## **Architecture Overview**

Reflex is built on a **three-plane architecture** designed for scalability, maintainability, and enterprise-grade performance:

### **Application Plane**
- **FastAPI Web Framework**: RESTful APIs and web dashboard
- **Celery Task Queue**: Asynchronous background processing
- **Redis Message Bus**: Inter-service communication
- **JWT Authentication**: Secure user management

### **Data Plane**
- **PostgreSQL**: Primary persistent storage
- **Vector Databases**: Knowledge base and embeddings
- **Redis Cache**: Session management and caching
- **File Storage**: Document and media storage

### **AI/ML Plane**
- **LangChain Framework**: AI orchestration and tool management
- **OpenAI GPT-4**: Primary language model
- **Whisper**: Speech-to-text transcription
- **Custom AI Chains**: Specialized executive functions

## **Technology Stack**

### **Backend**
- **Python 3.11+**: Core programming language
- **FastAPI**: Modern web framework with automatic API docs
- **SQLAlchemy 2.0**: ORM with async support
- **Alembic**: Database migrations
- **Pydantic**: Data validation and settings
- **Celery**: Distributed task queue
- **Redis**: Caching and message broker

### **AI/ML**
- **LangChain**: AI framework and tool orchestration
- **OpenAI GPT-4**: Primary language model
- **Whisper**: Speech recognition
- **Sentence Transformers**: Text embeddings
- **Weaviate/Pinecone**: Vector database options

### **Infrastructure**
- **Docker**: Containerization
- **Docker Compose**: Local development environment
- **Kubernetes**: Production orchestration
- **PostgreSQL**: Primary database
- **Prometheus/Grafana**: Monitoring and metrics

### **Integrations**
- **Slack API**: Team communication
- **Gmail API**: Email management
- **Asana API**: Project management
- **Stripe API**: Payment processing
- **Webhooks**: Real-time event processing

## **Project Structure**

```
reflex-ai-assistant/
├── src/                          # Main application code
│   ├── ai/                       # AI and ML components
│   │   ├── chain.py             # Core AI processing chain
│   │   ├── decision_engine.py   # Executive decision intelligence
│   │   ├── context_injector.py  # Strategic context injection
│   │   ├── prompts.py           # AI prompt templates
│   │   └── tools/               # AI tools and functions
│   ├── app.py                   # FastAPI application entry point
│   ├── config.py                # Configuration management
│   ├── auth/                    # Authentication and authorization
│   │   └── dependencies.py      # JWT and auth dependencies
│   ├── integrations/            # External service integrations
│   │   ├── slack_client.py      # Slack API client
│   │   ├── gmail_client.py      # Gmail API client
│   │   ├── asana_client.py      # Asana API client
│   │   ├── meeting_recorder.py  # Meeting transcription
│   │   └── webhooks/            # Webhook handlers
│   ├── jobs/                    # Background task processing
│   │   ├── celery_app.py        # Celery configuration
│   │   └── tasks/               # Celery task definitions
│   ├── storage/                 # Data persistence layer
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── db.py                # Database connection
│   │   └── migrations/          # Database migrations
│   ├── kb/                      # Knowledge base management
│   │   └── retriever.py         # Vector search and retrieval
│   ├── workflows/               # Workflow orchestration
│   │   ├── engine.py            # Workflow execution engine
│   │   └── router.py            # Event routing
│   ├── analytics/               # Analytics and telemetry
│   │   └── telemetry.py         # Usage tracking
│   └── logging/                 # Logging configuration
│       └── setup.py             # Logging setup
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── conftest.py              # Test configuration
├── deployments/                 # Deployment configurations
│   ├── docker/                  # Docker configurations
│   └── k8s/                     # Kubernetes manifests
├── scripts/                     # Utility scripts
│   ├── deploy.sh                # Deployment automation
│   ├── manage_db.py             # Database management
│   └── init-db.sql              # Database initialization
├── data/                        # Data storage
│   └── kb/                      # Knowledge base data
├── pyproject.toml               # Project dependencies
├── docker-compose.yml           # Local development environment
├── Dockerfile                   # Application containerization
├── alembic.ini                  # Database migration config
└── README.md                    # User-facing documentation
```

## **Development Setup**

### **Prerequisites**
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 14+
- Redis 7+
- Git

### **Quick Start**

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/reflex-ai-assistant.git
   cd reflex-ai-assistant
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start development environment**
   ```bash
   docker-compose up -d
   ```

4. **Initialize database**
   ```bash
   python scripts/manage_db.py init
   python scripts/manage_db.py upgrade
   ```

5. **Install dependencies**
   ```bash
   pip install -e .
   ```

6. **Run the application**
   ```bash
   uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
   ```

### **Environment Variables**

```bash
# Core Configuration
DATABASE_URL=postgresql://user:pass@localhost/reflex
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# AI/ML Configuration
OPENAI_API_KEY=your-openai-key
MODEL_NAME=gpt-4
EMBEDDING_MODEL=text-embedding-ada-002

# External Integrations
SLACK_BOT_TOKEN=your-slack-token
SLACK_SIGNING_SECRET=your-slack-secret
GMAIL_CREDENTIALS_FILE=path/to/credentials.json
ASANA_ACCESS_TOKEN=your-asana-token

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sparkroboticai@gmail.com
SMTP_PASSWORD=your-app-password

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

## **Core Components**

### **1. AI Chain (`src/ai/chain.py`)**

The core AI processing engine that orchestrates all AI interactions:

```python
class ReflexAIChain:
    """Main AI processing chain for Reflex Executive Assistant."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model=self.settings.model_name)
        self.tools = self._load_tools()
        self.memory = ConversationBufferMemory()
    
    async def process_message(self, message: str, user_id: str) -> str:
        """Process user message and return AI response."""
        # Tool selection and execution
        # Context injection
        # Response generation
```

**Key Features:**
- **Tool Orchestration**: Manages 15+ AI tools
- **Context Awareness**: Injects strategic context
- **Memory Management**: Maintains conversation history
- **Error Handling**: Graceful failure recovery

### **2. Decision Engine (`src/ai/decision_engine.py`)**

AI-powered executive decision support system:

```python
class ExecutiveDecisionEngine:
    """AI-powered decision support for executives."""
    
    async def analyze_decision(self, request: DecisionRequest) -> DecisionAnalysis:
        """Analyze decision with AI-powered insights."""
        # Risk assessment
        # Cultural impact analysis
        # Compliance checking
        # Auto-approval logic
```

**Key Features:**
- **Risk Assessment**: AI-powered risk analysis
- **Cultural Impact**: People-first decision making
- **Auto-approval**: Low-risk decision automation
- **Audit Trail**: Complete decision tracking

### **3. Context Injector (`src/ai/context_injector.py`)**

Strategic context injection system:

```python
class StrategicContextInjector:
    """Injects strategic context into communications."""
    
    async def inject_context(
        self,
        content: str,
        channel: CommunicationChannel,
        user_id: str
    ) -> ContextInjection:
        """Inject strategic context into communication."""
        # Context relevance analysis
        # Strategic alignment checking
        # Cultural sensitivity
        # Content enhancement
```

**Key Features:**
- **Context Types**: Values, Goals, Culture, Strategy, Well-being
- **Channel Optimization**: Platform-specific injection
- **Cultural Sensitivity**: Inclusive language
- **Alignment Tracking**: Strategic alignment scoring

### **4. Meeting Recorder (`src/integrations/meeting_recorder.py`)**

Automatic meeting transcription and analysis:

```python
class MeetingRecorder:
    """Records and analyzes executive meetings."""
    
    async def start_recording(self, meeting_id: str) -> bool:
        """Start recording meeting audio."""
        # Audio capture
        # Real-time processing
        # Speaker diarization
    
    async def analyze_transcript(self, meeting_id: str) -> MeetingAnalysis:
        """Analyze meeting transcript with AI."""
        # Action item extraction
        # Decision tracking
        # Cultural context analysis
```

**Key Features:**
- **Executive Control**: No participant consent required
- **Real-time Processing**: Live transcription
- **AI Analysis**: Action items and insights
- **Cultural Context**: Well-being and engagement tracking

## **API Documentation**

### **Core Endpoints**

#### **AI Processing**
```http
POST /api/ai/process
Content-Type: application/json

{
    "message": "How is our team performing?",
    "user_id": "executive_123",
    "context": {
        "channel": "voice",
        "urgency": "normal"
    }
}
```

#### **Decision Support**
```http
POST /api/decisions/analyze
Content-Type: application/json

{
    "decision_type": "budget_approval",
    "title": "Marketing Budget Increase",
    "amount": 50000,
    "requester": "marketing_director",
    "description": "Additional budget for Q4 campaigns"
}
```

#### **Context Injection**
```http
POST /api/context/inject
Content-Type: application/json

{
    "content": "Let's review the Q4 budget",
    "channel": "slack",
    "user_id": "executive_123"
}
```

#### **Meeting Management**
```http
POST /api/meetings/start
Content-Type: application/json

{
    "meeting_id": "meeting_123",
    "title": "Q4 Strategy Review",
    "participants": ["exec_1", "exec_2"]
}
```

### **Response Format**

All API responses follow a consistent format:

```json
{
    "status": "success|error",
    "data": {
        // Response data
    },
    "metadata": {
        "processing_time": 1.23,
        "model_used": "gpt-4",
        "confidence_score": 0.95
    }
}
```

## **Database Schema**

### **Core Tables**

#### **Users & Authentication**
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    subscription_tier VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API Keys for external access
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    permissions JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### **AI Processing**
```sql
-- Conversation history
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strategic context injections
CREATE TABLE strategic_contexts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    context_type VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    original_content TEXT NOT NULL,
    injected_content TEXT NOT NULL,
    final_content TEXT NOT NULL,
    alignment_score FLOAT NOT NULL,
    cultural_relevance FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### **Decision Intelligence**
```sql
-- Executive decisions
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    amount FLOAT,
    requester VARCHAR(255) NOT NULL,
    recommendation VARCHAR(20) NOT NULL,
    confidence_score FLOAT NOT NULL,
    reasoning TEXT NOT NULL,
    risk_assessment VARCHAR(20) NOT NULL,
    business_impact JSONB NOT NULL,
    compliance_check JSONB NOT NULL,
    auto_approval_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    required_approvals TEXT[] NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by VARCHAR(255),
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### **Meeting Management**
```sql
-- Meeting records
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    meeting_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    participants JSONB NOT NULL,
    recording_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Meeting transcripts
CREATE TABLE meeting_transcripts (
    id SERIAL PRIMARY KEY,
    meeting_id UUID REFERENCES meetings(id),
    transcript_text TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    confidence_score FLOAT,
    speaker_diarization JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## **Testing**

### **Test Structure**

```
tests/
├── unit/                    # Unit tests
│   ├── test_ai_chain.py    # AI chain unit tests
│   ├── test_models.py      # Database model tests
│   └── test_config.py      # Configuration tests
├── integration/            # Integration tests
│   ├── test_api.py         # API endpoint tests
│   ├── test_integrations.py # External service tests
│   └── test_workflows.py   # Workflow tests
└── conftest.py             # Test configuration and fixtures
```

### **Running Tests**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_ai_chain.py

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v
```

### **Test Configuration**

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///test.db")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()

@pytest.fixture
def client(test_db):
    """Create test client."""
    from src.app import app
    return TestClient(app)
```

## **Deployment**

### **Docker Deployment**

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or build individual services
docker build -t reflex-ai:latest .
docker run -p 8000:8000 reflex-ai:latest
```

### **Kubernetes Deployment**

```bash
# Apply Kubernetes manifests
kubectl apply -f deployments/k8s/

# Check deployment status
kubectl get pods -n reflex
kubectl get services -n reflex
```

### **Production Configuration**

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/reflex
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=reflex
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

## **Contributing**

### **Development Workflow**

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**
   ```bash
   # Run tests
   pytest
   
   # Check code quality
   ruff check src/
   black src/
   ```

3. **Commit with conventional commits**
   ```bash
   git commit -m "feat: add new AI tool for email analysis"
   ```

4. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### **Code Standards**

- **Python**: Follow PEP 8 with Black formatting
- **Type Hints**: Use type hints for all functions
- **Documentation**: Docstrings for all public functions
- **Testing**: 90%+ test coverage required
- **Commits**: Use conventional commit format

### **Conventional Commits**

```
feat: add new AI tool for email analysis
fix: resolve issue with context injection
docs: update API documentation
test: add unit tests for decision engine
refactor: improve error handling in AI chain
```

### **Pull Request Process**

1. **Create descriptive PR title**
2. **Add detailed description**
3. **Include test coverage**
4. **Update documentation**
5. **Request code review**
6. **Address feedback**
7. **Merge when approved**

## **Monitoring & Observability**

### **Metrics Collection**

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# Custom metrics
ai_requests_total = Counter('ai_requests_total', 'Total AI requests')
decision_processing_time = Histogram('decision_processing_time', 'Decision processing time')
active_users = Gauge('active_users', 'Number of active users')
```

### **Logging**

```python
# Structured logging
import logging
import json

logger = logging.getLogger(__name__)

def log_ai_request(user_id: str, message: str, response_time: float):
    logger.info("AI request processed", extra={
        "user_id": user_id,
        "message_length": len(message),
        "response_time": response_time,
        "event_type": "ai_request"
    })
```

### **Health Checks**

```python
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "ai_model": "healthy"
        }
    }
```

## **Security**

### **Authentication & Authorization**

- **JWT Tokens**: Secure user authentication
- **API Keys**: External service access
- **Role-based Access**: User permission management
- **Rate Limiting**: API abuse prevention

### **Data Protection**

- **Encryption**: Data at rest and in transit
- **PII Redaction**: Automatic sensitive data removal
- **Audit Logging**: Complete access tracking
- **Compliance**: GDPR, SOC 2, ISO 27001 ready

### **Security Headers**

```python
# Security middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reflex.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## **Performance Optimization**

### **Caching Strategy**

```python
# Redis caching
import redis
from functools import wraps

redis_client = redis.Redis.from_url(settings.redis_url)

def cache_result(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

### **Database Optimization**

```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### **Async Processing**

```python
# Background task processing
from celery import Celery

celery_app = Celery("reflex")
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
)
```

---

## **Support & Resources**

### **Documentation**
- [API Reference](https://docs.reflex.ai/api)
- [Integration Guide](https://docs.reflex.ai/integrations)
- [Deployment Guide](https://docs.reflex.ai/deployment)

### **Community**
- [GitHub Issues](https://github.com/your-org/reflex-ai-assistant/issues)
- [Discord Community](https://discord.gg/reflex-ai)
- [Developer Blog](https://blog.reflex.ai)

### **Contact**
- **Technical Support**: dev-support@reflex.ai
- **Security Issues**: security@reflex.ai
- **Partnerships**: partnerships@reflex.ai

---

*"Building the future of executive leadership, one commit at a time."* 