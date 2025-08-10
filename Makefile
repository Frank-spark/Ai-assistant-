# Reflex AI Assistant - Development Makefile
# Senior developer-friendly commands for local development and deployment

.PHONY: help dev test lint format clean build deploy demo

# Default target
help:
	@echo "Reflex AI Assistant - Development Commands"
	@echo "=========================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make dev-app      - Start FastAPI application only"
	@echo "  make dev-workers  - Start Celery workers only"
	@echo "  make dev-db       - Start PostgreSQL database only"
	@echo "  make dev-redis    - Start Redis server only"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo "  make test-watch   - Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with Black"
	@echo "  make type-check   - Run type checking with MyPy"
	@echo "  make security-check - Run security scanning"
	@echo ""
	@echo "Database:"
	@echo "  make db-init      - Initialize database"
	@echo "  make db-migrate   - Run database migrations"
	@echo "  make db-seed      - Load demo data"
	@echo "  make db-reset     - Reset database (WARNING: destructive)"
	@echo ""
	@echo "Demo & Deployment:"
	@echo "  make demo         - Start demo environment"
	@echo "  make demo-data    - Load demo data"
	@echo "  make build        - Build Docker image"
	@echo "  make deploy-staging - Deploy to staging"
	@echo "  make deploy-production - Deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make logs         - Show application logs"
	@echo "  make shell        - Open shell in container"
	@echo "  make backup       - Backup database"

# Development Environment
dev: dev-db dev-redis dev-app dev-workers
	@echo "Development environment started!"
	@echo "Dashboard: http://localhost:8000/dashboard"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Grafana: http://localhost:3000 (admin/demo123)"

dev-app:
	@echo "Starting FastAPI application..."
	uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

dev-workers:
	@echo "Starting Celery workers..."
	celery -A src.jobs.celery_app worker --loglevel=info --concurrency=2

dev-db:
	@echo "Starting PostgreSQL database..."
	docker-compose up -d demo-db

dev-redis:
	@echo "Starting Redis server..."
	docker-compose up -d demo-redis

# Testing
test:
	@echo "Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

test-watch:
	@echo "Running tests in watch mode..."
	pytest tests/ -f -v

# Code Quality
lint:
	@echo "Running linting checks..."
	ruff check src/ tests/
	black --check src/ tests/

format:
	@echo "Formatting code..."
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	@echo "Running type checking..."
	mypy src/ --ignore-missing-imports

security-check:
	@echo "Running security scan..."
	bandit -r src/ -f json -o security-report.json
	@echo "Security scan complete. Check security-report.json for details."

# Database Management
db-init:
	@echo "Initializing database..."
	python scripts/manage_db.py init

db-migrate:
	@echo "Running database migrations..."
	python scripts/manage_db.py upgrade

db-seed:
	@echo "Loading demo data..."
	python scripts/load_demo_data.py

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "Resetting database..."
	python scripts/manage_db.py reset
	python scripts/load_demo_data.py

# Demo Environment
demo:
	@echo "Starting demo environment..."
	docker-compose -f docker-compose.demo.yml up -d
	@echo "Demo environment started!"
	@echo "Dashboard: http://localhost:8000/dashboard"
	@echo "Analytics: http://localhost:8000/analytics"
	@echo "Revenue: http://localhost:8000/revenue"

demo-data:
	@echo "Loading demo data..."
	docker-compose -f docker-compose.demo.yml exec reflex-app python scripts/load_demo_data.py

# Building and Deployment
build:
	@echo "Building Docker image..."
	docker build -t reflex-ai:latest .

deploy-staging:
	@echo "Deploying to staging..."
	kubectl apply -f deployments/k8s/staging/
	kubectl rollout status deployment/reflex-staging

deploy-production:
	@echo "Deploying to production..."
	kubectl apply -f deployments/k8s/production/
	kubectl rollout status deployment/reflex-production

# Utilities
clean:
	@echo "Cleaning build artifacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf security-report.json

logs:
	@echo "Showing application logs..."
	docker-compose logs -f reflex-app

shell:
	@echo "Opening shell in container..."
	docker-compose exec reflex-app /bin/bash

backup:
	@echo "Creating database backup..."
	docker-compose exec demo-db pg_dump -U reflex reflex_demo > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Health Checks
health:
	@echo "Checking system health..."
	@curl -f http://localhost:8000/health || echo "Application not responding"
	@docker-compose ps

# Performance Testing
perf-test:
	@echo "Running performance tests..."
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Documentation
docs:
	@echo "Generating documentation..."
	pdoc --html src/ --output-dir docs/api
	@echo "Documentation generated in docs/api/"

# Development Setup
setup:
	@echo "Setting up development environment..."
	pip install -e .
	pre-commit install
	@echo "Development environment setup complete!"

# Quick Commands for Common Tasks
start: dev
stop:
	@echo "Stopping development environment..."
	docker-compose down

restart: stop start

# Database Quick Commands
db: db-migrate db-seed

# Test Quick Commands
check: lint type-check test

# Deployment Quick Commands
ship: test check build deploy-staging

# Monitoring
monitor:
	@echo "Opening monitoring dashboards..."
	@echo "Grafana: http://localhost:3000"
	@echo "Prometheus: http://localhost:9090"
	@echo "Application: http://localhost:8000/health"

# Development Helpers
new-feature:
	@read -p "Feature name: " feature; \
	git checkout -b feature/$$feature; \
	echo "Created feature branch: feature/$$feature"

new-bugfix:
	@read -p "Bug description: " bug; \
	git checkout -b bugfix/$$bug; \
	echo "Created bugfix branch: bugfix/$$bug"

# Environment Management
env-dev:
	@echo "Setting up development environment variables..."
	cp env.example .env
	@echo "Edit .env with your development configuration"

env-prod:
	@echo "Setting up production environment variables..."
	cp env.example .env.prod
	@echo "Edit .env.prod with your production configuration"

# Database Schema
schema:
	@echo "Generating database schema..."
	python scripts/manage_db.py generate-schema

# API Documentation
api-docs:
	@echo "Generating API documentation..."
	python scripts/generate_api_docs.py

# Security
security-audit:
	@echo "Running security audit..."
	safety check
	bandit -r src/
	semgrep --config=auto src/

# Performance
benchmark:
	@echo "Running performance benchmarks..."
	python scripts/benchmark.py

# Release Management
release:
	@read -p "Release version (e.g., 1.2.3): " version; \
	bumpversion patch --new-version $$version; \
	git push origin main --tags; \
	echo "Released version $$version"

# Quick Development Workflow
workflow:
	@echo "Starting development workflow..."
	@echo "1. Starting development environment..."
	make dev
	@echo "2. Running tests..."
	make test
	@echo "3. Checking code quality..."
	make check
	@echo "4. Opening dashboard..."
	@echo "Dashboard: http://localhost:8000/dashboard" 