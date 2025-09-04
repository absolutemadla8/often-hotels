.PHONY: help build up down logs shell test lint format clean migrate

# Default environment
ENV ?= dev

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Often Hotels API - Development Commands$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the Docker images
	@echo "$(BLUE)Building Docker images...$(RESET)"
	docker-compose build

up: ## Start all services
	@echo "$(BLUE)Starting all services...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)Services started! API available at http://localhost:8000$(RESET)"

down: ## Stop all services
	@echo "$(BLUE)Stopping all services...$(RESET)"
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

logs-app: ## Show logs from app service only
	docker-compose logs -f app

shell: ## Open a shell in the app container
	docker-compose exec app bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec db psql -U postgres -d often_hotels

redis-shell: ## Open Redis shell
	docker-compose exec redis redis-cli

test: ## Run tests
	@echo "$(BLUE)Running tests...$(RESET)"
	docker-compose exec app pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	docker-compose exec app pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint: ## Run linting
	@echo "$(BLUE)Running linting...$(RESET)"
	docker-compose exec app black app/ tests/
	docker-compose exec app isort app/ tests/
	docker-compose exec app flake8 app/ tests/

format: ## Format code
	@echo "$(BLUE)Formatting code...$(RESET)"
	docker-compose exec app black app/ tests/
	docker-compose exec app isort app/ tests/

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(RESET)"
	docker-compose exec app alembic upgrade head

migrate-auto: ## Generate automatic migration
	@echo "$(BLUE)Generating automatic migration...$(RESET)"
	@read -p "Enter migration message: " msg; \
	docker-compose exec app alembic revision --autogenerate -m "$$msg"

migrate-create: ## Create new empty migration
	@echo "$(BLUE)Creating new migration...$(RESET)"
	@read -p "Enter migration message: " msg; \
	docker-compose exec app alembic revision -m "$$msg"

migrate-history: ## Show migration history
	docker-compose exec app alembic history

migrate-current: ## Show current migration
	docker-compose exec app alembic current

seed-db: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(RESET)"
	docker-compose exec app python -c "from app.db.init_db import init_db; import asyncio; asyncio.run(init_db())"

clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(RESET)"
	docker-compose down -v --remove-orphans
	docker system prune -f

clean-all: ## Clean up all Docker resources including images
	@echo "$(RED)Cleaning up ALL Docker resources...$(RESET)"
	docker-compose down -v --remove-orphans
	docker system prune -a -f

restart: down up ## Restart all services

rebuild: clean build up ## Rebuild and restart all services

status: ## Show status of all services
	docker-compose ps

# Production commands
prod-build: ## Build production images
	@echo "$(BLUE)Building production images...$(RESET)"
	docker-compose -f docker-compose.prod.yml build

prod-up: ## Start production services
	@echo "$(BLUE)Starting production services...$(RESET)"
	docker-compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production services
	docker-compose -f docker-compose.prod.yml down

prod-logs: ## Show production logs
	docker-compose -f docker-compose.prod.yml logs -f

# Development helpers
install: ## Install development dependencies locally
	pip install -r requirements.txt
	pip install -e .

dev-server: ## Run development server locally (without Docker)
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

create-env: ## Create .env file from template
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN).env file created from template$(RESET)"; \
		echo "$(BLUE)Please edit .env file with your configuration$(RESET)"; \
	else \
		echo "$(RED).env file already exists$(RESET)"; \
	fi

# SSL certificates for development
ssl-cert: ## Generate self-signed SSL certificate for development
	@echo "$(BLUE)Generating SSL certificate for development...$(RESET)"
	mkdir -p nginx/ssl
	openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout nginx/ssl/key.pem \
		-out nginx/ssl/cert.pem \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
	@echo "$(GREEN)SSL certificate generated!$(RESET)"

# Monitoring
monitor: ## Open monitoring dashboards
	@echo "$(BLUE)Opening monitoring dashboards...$(RESET)"
	@echo "$(GREEN)Grafana: http://localhost:3000 (admin/admin)$(RESET)"
	@echo "$(GREEN)Prometheus: http://localhost:9090$(RESET)"

# Database operations
db-backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(RESET)"
	docker-compose exec db pg_dump -U postgres often_hotels > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backup created!$(RESET)"

db-restore: ## Restore database from backup
	@echo "$(BLUE)Restoring database...$(RESET)"
	@read -p "Enter backup file path: " backup; \
	docker-compose exec -T db psql -U postgres -d often_hotels < "$$backup"

# Security
security-scan: ## Run security scan on dependencies
	@echo "$(BLUE)Running security scan...$(RESET)"
	docker-compose exec app safety check
	docker-compose exec app bandit -r app/

# API testing
api-test: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(RESET)"
	curl -f http://localhost:8000/health || echo "$(RED)Health check failed$(RESET)"
	curl -f http://localhost:8000/api/v1/hotels/ || echo "$(RED)Hotels endpoint failed$(RESET)"