# RSAI Microservices Makefile

.PHONY: help build up down restart logs clean test lint format install-dev docs

# Default target
help:
	@echo "RSAI Microservices Development Commands"
	@echo "========================================"
	@echo "setup          - Initial project setup"
	@echo "build          - Build all Docker images"
	@echo "up             - Start all services"
	@echo "down           - Stop all services"
	@echo "restart        - Restart all services"
	@echo "logs           - View service logs"
	@echo "clean          - Clean up containers and volumes"
	@echo "test           - Run all tests"
	@echo "test-service   - Run tests for specific service (SERVICE=service-name)"
	@echo "lint           - Run code linting"
	@echo "format         - Format code"
	@echo "install-dev    - Install development dependencies"
	@echo "docs           - Generate documentation"
	@echo "migration      - Run database migrations"
	@echo "seed-data      - Load sample data"

# Development setup
setup:
	@echo "Setting up RSAI Microservices development environment..."
	@make install-dev
	@make build
	@echo "Setup complete! Run 'make up' to start services."

install-dev:
	@echo "Installing development dependencies..."
	@pip install -r requirements-dev.txt
	@pre-commit install

# Docker operations
build:
	@echo "Building all Docker images..."
	@docker-compose build

up:
	@echo "Starting all services..."
	@docker-compose up -d
	@echo "Services started. Access API Gateway at http://localhost:8000"
	@echo "View service logs with 'make logs'"

down:
	@echo "Stopping all services..."
	@docker-compose down

restart:
	@echo "Restarting all services..."
	@docker-compose restart

logs:
	@docker-compose logs -f

clean:
	@echo "Cleaning up containers and volumes..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f

# Testing
test:
	@echo "Running all tests..."
	@pytest tests/ -v --cov=services --cov-report=html --cov-report=term

test-service:
	@echo "Running tests for $(SERVICE)..."
	@cd services/$(SERVICE) && pytest tests/ -v

# Code quality
lint:
	@echo "Running code linting..."
	@flake8 services/ shared/ tests/
	@mypy services/ shared/

format:
	@echo "Formatting code..."
	@black services/ shared/ tests/
	@isort services/ shared/ tests/

# Database operations
migration:
	@echo "Running database migrations..."
	@docker-compose exec data-ingestion alembic upgrade head
	@docker-compose exec data-validation alembic upgrade head
	@docker-compose exec geography alembic upgrade head
	@docker-compose exec index-calculation alembic upgrade head
	@docker-compose exec export alembic upgrade head
	@docker-compose exec orchestration alembic upgrade head
	@docker-compose exec configuration alembic upgrade head

seed-data:
	@echo "Loading sample data..."
	@python scripts/seed_data.py

# Documentation
docs:
	@echo "Generating documentation..."
	@sphinx-build -b html docs/ docs/_build/html
	@echo "Documentation generated in docs/_build/html/"

# Monitoring
monitor:
	@echo "Opening monitoring dashboards..."
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

# Development utilities
shell:
	@echo "Opening shell in $(SERVICE) service..."
	@docker-compose exec $(SERVICE) /bin/bash

logs-service:
	@echo "Viewing logs for $(SERVICE)..."
	@docker-compose logs -f $(SERVICE)

scale:
	@echo "Scaling $(SERVICE) to $(REPLICAS) instances..."
	@docker-compose up -d --scale $(SERVICE)=$(REPLICAS)

# Production deployment
deploy-prod:
	@echo "Deploying to production..."
	@docker-compose -f docker-compose.prod.yml up -d

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "API Gateway: UNHEALTHY"
	@curl -f http://localhost:8001/health || echo "Data Ingestion: UNHEALTHY" 
	@curl -f http://localhost:8002/health || echo "Data Validation: UNHEALTHY"
	@curl -f http://localhost:8003/health || echo "Geography: UNHEALTHY"
	@curl -f http://localhost:8004/health || echo "Index Calculation: UNHEALTHY"
	@curl -f http://localhost:8005/health || echo "Export: UNHEALTHY"
	@curl -f http://localhost:8006/health || echo "Orchestration: UNHEALTHY"
	@curl -f http://localhost:8007/health || echo "Configuration: UNHEALTHY"

# Performance testing
perf-test:
	@echo "Running performance tests..."
	@locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Security scanning
security:
	@echo "Running security scans..."
	@bandit -r services/ shared/
	@safety check

# Backup and restore
backup:
	@echo "Creating database backup..."
	@docker-compose exec postgres pg_dumpall -U rsai > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore:
	@echo "Restoring database from $(BACKUP_FILE)..."
	@docker-compose exec -T postgres psql -U rsai < $(BACKUP_FILE)