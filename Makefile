.PHONY: help install dev test lint format clean docker-build docker-up docker-down

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "AIOps - AI-Powered DevOps Automation Platform"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

dev: ## Run development server
	uvicorn aiops.api.app:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	pytest --cov=aiops --cov-report=html --cov-report=term

test-verbose: ## Run tests with verbose output
	pytest -v --cov=aiops --cov-report=html

lint: ## Run linters
	flake8 aiops/
	mypy aiops/

format: ## Format code
	black aiops/
	isort aiops/

clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-restart: ## Restart all services
	docker-compose restart

db-migrate: ## Run database migrations
	alembic upgrade head

db-rollback: ## Rollback last migration
	alembic downgrade -1

db-reset: ## Reset database
	docker-compose down -v
	docker-compose up -d postgres
	sleep 5
	alembic upgrade head

cli: ## Run CLI
	python -m aiops.cli.main

api-docs: ## Open API documentation
	@echo "Opening API docs at http://localhost:8000/docs"
	@python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')"

monitoring: ## Open monitoring dashboards
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "Jaeger: http://localhost:16686"

setup: ## Initial project setup
	@echo "Setting up AIOps project..."
	@cp .env.example .env
	@echo "✅ Created .env file (please configure your API keys)"
	@make install
	@echo "✅ Installed dependencies"
	@make docker-up
	@echo "✅ Started Docker services"
	@sleep 10
	@make db-migrate
	@echo "✅ Ran database migrations"
	@echo ""
	@echo "🎉 Setup complete! Run 'make dev' to start the development server"

quick-start: setup dev ## Quick start (setup + dev server)
