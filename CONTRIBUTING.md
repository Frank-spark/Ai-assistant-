# Contributing to Reflex AI Assistant

Thank you for your interest in contributing to Reflex AI Assistant! This document provides guidelines for developers who want to contribute to our executive AI platform.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Environment](#development-environment)
- [Architecture Overview](#architecture-overview)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Standards](#code-standards)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 14+
- Redis 7+
- Git

### One-Command Setup

```bash
# Clone the repository
git clone https://github.com/your-org/reflex-ai-assistant.git
cd reflex-ai-assistant

# Start development environment
make dev

# Or using Docker Compose
docker-compose -f docker-compose.dev.yml up -d
```

### Verify Installation

```bash
# Check application health
curl http://localhost:8000/health

# Run tests
make test

# Check code quality
make lint
```

## Development Environment

### Local Development Setup

1. **Environment Configuration**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

2. **Database Setup**
   ```bash
   # Initialize database
   python scripts/manage_db.py init
   python scripts/manage_db.py upgrade
   
   # Load demo data
   python scripts/load_demo_data.py
   ```

3. **Start Services**
   ```bash
   # Start all services
   make dev
   
   # Or start individually
   make start-app      # FastAPI application
   make start-workers  # Celery workers
   make start-redis    # Redis server
   make start-db       # PostgreSQL
   ```

### Development URLs

- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Executive Dashboard**: http://localhost:8000/dashboard
- **Grafana**: http://localhost:3000 (admin/demo123)
- **Prometheus**: http://localhost:9090
- **MailHog**: http://localhost:8025

## Architecture Overview

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Layer     │    │   AI Engine     │
│   (Dashboard)   │◄──►│   (FastAPI)     │◄──►│   (LangChain)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Task Queue    │    │   Database      │    │   Integrations  │
│   (Celery)      │◄──►│   (PostgreSQL)  │◄──►│   (Slack/Gmail) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components

- **Application Layer**: FastAPI web framework with async support
- **AI Engine**: LangChain-based AI processing with custom tools
- **Task Queue**: Celery for background processing
- **Data Layer**: PostgreSQL with SQLAlchemy ORM
- **Cache Layer**: Redis for session and task management
- **Integration Layer**: External service connectors (Slack, Gmail, Asana)

### Directory Structure

```
reflex-ai-assistant/
├── src/                    # Main application code
│   ├── ai/                # AI and ML components
│   ├── app.py             # FastAPI application entry point
│   ├── auth/              # Authentication and authorization
│   ├── integrations/      # External service integrations
│   ├── jobs/              # Background task processing
│   ├── storage/           # Data persistence layer
│   ├── workflows/         # Workflow orchestration
│   └── analytics/         # Analytics and telemetry
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── deployments/           # Deployment configurations
├── docs/                  # Documentation
└── migrations/            # Database migrations
```

## Development Workflow

### Branch Strategy

We use a feature branch workflow:

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add new AI tool for email analysis"

# Push and create pull request
git push origin feature/your-feature-name
```

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new AI tool for email analysis
fix: resolve issue with context injection
docs: update API documentation
test: add unit tests for decision engine
refactor: improve error handling in AI chain
```

### Code Review Process

1. **Create Pull Request** with clear description
2. **Automated Checks** must pass (tests, linting, security)
3. **Code Review** by at least one senior developer
4. **Address Feedback** and update PR
5. **Merge** when approved

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                  # Unit tests
│   ├── test_ai_chain.py  # AI chain unit tests
│   ├── test_models.py    # Database model tests
│   └── test_config.py    # Configuration tests
├── integration/           # Integration tests
│   ├── test_api.py       # API endpoint tests
│   ├── test_integrations.py # External service tests
│   └── test_workflows.py # Workflow tests
└── conftest.py           # Test configuration
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/unit/test_ai_chain.py

# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest -v
```

### Test Coverage Requirements

- **Minimum Coverage**: 80% for new code
- **Critical Paths**: 90% coverage required
- **Integration Tests**: All external integrations must be tested
- **Performance Tests**: Load testing for critical endpoints

### Writing Tests

```python
import pytest
from src.ai.chain import ReflexAIChain

class TestReflexAIChain:
    def test_process_message_success(self):
        """Test successful message processing."""
        chain = ReflexAIChain()
        result = chain.process_message("Hello", "user_123")
        assert result is not None
        assert "response" in result

    def test_process_message_invalid_input(self):
        """Test message processing with invalid input."""
        chain = ReflexAIChain()
        with pytest.raises(ValueError):
            chain.process_message("", "user_123")
```

## Code Standards

### Python Standards

- **Python Version**: 3.11+
- **Style Guide**: PEP 8 with Black formatting
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style docstrings for all public functions

### Code Quality Tools

```bash
# Format code
make format

# Lint code
make lint

# Type checking
make type-check

# Security scanning
make security-check
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks
pre-commit run --all-files
```

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Type hints are present
- [ ] Docstrings are complete
- [ ] Tests are written and passing
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] Error handling is appropriate
- [ ] Logging is implemented

## Pull Request Process

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

### Review Process

1. **Automated Checks**
   - Tests must pass
   - Code coverage maintained
   - Security scan clean
   - Performance benchmarks met

2. **Code Review**
   - At least one senior developer approval
   - Architecture review for major changes
   - Security review for sensitive changes

3. **Final Steps**
   - Documentation updated
   - Release notes prepared
   - Deployment plan reviewed

## Release Process

### Version Management

We use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Steps

1. **Prepare Release**
   ```bash
   # Update version
   bumpversion patch  # or minor/major
   
   # Update changelog
   make update-changelog
   ```

2. **Create Release**
   ```bash
   # Create release branch
   git checkout -b release/v1.2.0
   
   # Tag release
   git tag v1.2.0
   git push origin v1.2.0
   ```

3. **Deploy**
   ```bash
   # Deploy to staging
   make deploy-staging
   
   # Run smoke tests
   make smoke-tests
   
   # Deploy to production
   make deploy-production
   ```

### Hotfix Process

For critical bug fixes:

1. Create hotfix branch from production
2. Fix the issue
3. Add regression test
4. Deploy immediately
5. Merge back to main

## Getting Help

### Resources

- **Documentation**: [docs/](docs/)
- **Architecture Guide**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API Reference**: http://localhost:8000/docs
- **Issues**: [GitHub Issues](https://github.com/your-org/reflex-ai-assistant/issues)

### Communication

- **Slack**: #reflex-dev (for internal team)
- **Email**: dev-team@reflex.ai
- **Office Hours**: Tuesdays 2-3 PM EST

### Mentorship

New contributors are paired with experienced team members:

- **Code Reviews**: Senior developers provide detailed feedback
- **Architecture Sessions**: Weekly sessions to discuss system design
- **Pair Programming**: Available for complex features

## Recognition

We recognize contributions through:

- **Contributor Hall of Fame**: Listed in README.md
- **Release Notes**: Contributors credited in each release
- **Team Recognition**: Monthly shoutouts for significant contributions

---

Thank you for contributing to Reflex AI Assistant! Your work helps executives lead better and create exceptional workplaces. 