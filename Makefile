.PHONY: help install test lint format clean deploy migrate backup restore

help: ## Show this help message
	@echo "Nebula Search Engine - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Dependencies installed"

dev: ## Start development environment
	@echo "Starting development environment..."
	docker-compose up -d postgres redis
	@echo "✅ Development environment started"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "API Docs: http://localhost:8000/docs"

dev-backend: ## Start backend in development mode
	@echo "Starting backend..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend in development mode
	@echo "Starting frontend..."
	cd frontend && npm run dev

test: ## Run all tests
	@echo "Running all tests..."
	cd backend && pytest --cov=app --cov-report=term-missing
	cd frontend && npm test

test-backend: ## Run backend tests only
	@echo "Running backend tests..."
	cd backend && pytest --cov=app --cov-report=term-missing

test-frontend: ## Run frontend tests only
	@echo "Running frontend tests..."
	cd frontend && npm test

test-e2e: ## Run frontend end-to-end tests
	@echo "Running frontend E2E tests..."
	cd frontend && npm run e2e

test-e2e-backend: ## Run backend E2E tests (requires server on localhost:8000)
	@echo "Running backend E2E tests..."
	@echo "⚠️  Ensure backend is running on http://localhost:8000"
	cd backend && python -m pytest ../tests/e2e/ -v

test-performance: ## Run performance tests
	@echo "Running performance tests..."
	cd tests/performance && python -m pytest

lint: ## Run all linters
	@echo "Running linters..."
	cd backend && ruff check app/
	cd frontend && npm run lint

format: ## Format all code
	@echo "Formatting code..."
	cd backend && ruff format app/
	cd frontend && npm run format

typecheck: ## Run type checking
	@echo "Running type checks..."
	cd backend && mypy app/
	cd frontend && npm run typecheck

security: ## Run security scans
	@echo "Running security scans..."
	cd backend && safety check
	cd backend && bandit -r app/
	cd backend && pip-audit

build: ## Build Docker images
	@echo "Building Docker images..."
	docker-compose build

build-backend: ## Build backend Docker image
	@echo "Building backend image..."
	docker build -t nebula-backend:latest docker/

build-frontend: ## Build frontend Docker image
	@echo "Building frontend image..."
	docker build -t nebula-frontend:latest docker/frontend/

deploy: ## Deploy to production
	@echo "Deploying to production..."
	@echo "⚠️  This will deploy to production. Are you sure? (y/n)"
	@read -p "" confirm; [ "$$confirm" = "y" ]
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Deployed to production"

deploy-k8s: ## Deploy to Kubernetes
	@echo "Deploying to Kubernetes..."
	kubectl apply -f infrastructure/k8s/
	@echo "✅ Deployed to Kubernetes"

migrate: ## Run database migrations
	@echo "Running database migrations..."
	cd backend && alembic upgrade head
	@echo "✅ Migrations complete"

migrate-create: ## Create new migration
	@echo "Creating new migration..."
	@read -p "Migration message: " msg; cd backend && alembic revision --autogenerate -m "$$msg"
	@echo "✅ Migration created"

seed: ## Seed database with sample data
	@echo "Seeding database..."
	cd backend && python -m app.database.seeds.main
	@echo "✅ Database seeded"

backup: ## Backup database
	@echo "Backing up database..."
	@mkdir -p database/backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	pg_dump -h localhost -U nebula -d nebula > database/backups/nebula_$$timestamp.sql
	@echo "✅ Backup created: database/backups/nebula_$$timestamp.sql"

restore: ## Restore database from backup
	@echo "Restoring database..."
	@read -p "Backup file: " file; psql -h localhost -U nebula -d nebula < $$file
	@echo "✅ Database restored"

logs: ## Show application logs
	docker-compose logs -f

logs-backend: ## Show backend logs
	docker-compose logs -f backend

logs-frontend: ## Show frontend logs
	docker-compose logs -f frontend

clean: ## Clean up temporary files
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name node_modules -exec rm -rf {} +
	find . -type d -name .next -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✅ Cleanup complete"

clean-docker: ## Clean Docker resources
	@echo "Cleaning Docker resources..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Docker cleaned"

monitor: ## Start monitoring stack
	@echo "Starting monitoring stack..."
	docker-compose -f infrastructure/monitoring/docker-compose.monitoring.yml up -d
	@echo "✅ Monitoring started"
	@echo "Grafana: http://localhost:3000"
	@echo "Prometheus: http://localhost:9090"

monitor-stop: ## Stop monitoring stack
	@echo "Stopping monitoring stack..."
	docker-compose -f infrastructure/monitoring/docker-compose.monitoring.yml down
	@echo "✅ Monitoring stopped"

shell-backend: ## Open backend shell
	docker-compose exec backend bash

shell-postgres: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U nebula -d nebula

shell-redis: ## Open Redis shell
	docker-compose exec redis redis-cli

health: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health > /dev/null && echo "✅ Backend: Healthy" || echo "❌ Backend: Unhealthy"
	@curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend: Healthy" || echo "❌ Frontend: Unhealthy"
	@docker-compose exec -T postgres pg_isready -U nebula > /dev/null 2>&1 && echo "✅ PostgreSQL: Healthy" || echo "❌ PostgreSQL: Unhealthy"
	@docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "✅ Redis: Healthy" || echo "❌ Redis: Unhealthy"

benchmark: ## Run performance benchmarks
	@echo "Running benchmarks..."
	cd tests/performance && python benchmarks.py
	@echo "✅ Benchmarks complete"

load-test: ## Run load tests
	@echo "Running load tests..."
	cd tests/load && locust -f locustfile.py --headless -u 100 -r 10 -t 1m

docs: ## Generate documentation
	@echo "Generating documentation..."
	cd backend && python -m app.docs.generator
	@echo "✅ Documentation generated"

docs-serve: ## Serve documentation locally
	@echo "Serving documentation..."
	cd docs && python -m http.server 8080
	@echo "✅ Documentation available at http://localhost:8080"

update: ## Update all dependencies
	@echo "Updating backend dependencies..."
	cd backend && pip install --upgrade -r requirements.txt
	@echo "Updating frontend dependencies..."
	cd frontend && npm update
	@echo "✅ Dependencies updated"

info: ## Show system information
	@echo "Nebula Search Engine - System Information"
	@echo "========================================"
	@echo "Python: $$(python --version 2>&1)"
	@echo "Node: $$(node --version 2>&1)"
	@echo "Docker: $$(docker --version 2>&1)"
	@echo "Docker Compose: $$(docker-compose --version 2>&1)"
	@echo "PostgreSQL: $$(docker-compose exec -T postgres psql -V 2>&1 | head -n1)"
	@echo "Redis: $$(docker-compose exec -T redis redis-cli --version 2>&1)"

.DEFAULT_GOAL := help