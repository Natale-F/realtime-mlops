.PHONY: help install install-dev lint format check test clean

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	# Or: pip install -e ".[dev]"

lint:  ## Run ruff linter
	ruff check src/ tests/

format:  ## Format code with ruff
	ruff format src/ tests/

format-check:  ## Check formatting without modifying files
	ruff format --check src/ tests/

check:  ## Run all checks (lint + format-check)
	ruff check src/ tests/
	ruff format --check src/ tests/

fix:  ## Auto-fix linting issues
	ruff check --fix src/ tests/
	ruff format src/ tests/

test:  ## Run tests
	pytest tests/

test-cov:  ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

type-check:  ## Run mypy type checker
	mypy src/

clean:  ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage
	rm -rf dist build *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Generator commands
generator-dev:  ## Run generator in dev mode
	python -m src.generator.generate --config dev --duration 30

generator-normal:  ## Run generator in normal mode
	python -m src.generator.generate --config normal

generator-chaos:  ## Run generator in chaos mode
	python -m src.generator.generate --config chaos --duration 300

# Consumer commands
consumer-storage:  ## Run storage consumer locally
	python -m src.consumers.storage.consume

consumer-storage-debug:  ## Run storage consumer with debug logging
	python -m src.consumers.storage.consume --log-level DEBUG

# Docker commands
docker-build:  ## Build Docker image
	docker compose build

docker-up:  ## Start all Docker services
	docker compose up -d

docker-up-infra:  ## Start only infrastructure (Kafka, Postgres, Kafka UI)
	docker compose up -d zookeeper kafka postgres kafka-ui

docker-up-generator:  ## Start generator
	docker compose up generator

docker-down:  ## Stop Docker services
	docker compose down

docker-down-clean:  ## Stop and remove volumes (reset data)
	docker compose down -v

docker-logs:  ## View all Docker logs
	docker compose logs -f

docker-logs-generator:  ## View generator logs
	docker compose logs -f generator

docker-logs-consumer:  ## View storage consumer logs
	docker compose logs -f storage-consumer

docker-logs-kafka:  ## View Kafka logs
	docker compose logs -f kafka

docker-restart:  ## Restart all services
	docker compose restart

docker-ps:  ## Show running containers
	docker compose ps

# Development workflow
dev-setup:  ## Complete development setup
	$(MAKE) install-dev
	$(MAKE) check
	@echo "✅ Development environment ready!"

ci-check:  ## Run all CI checks
	$(MAKE) check
	$(MAKE) test-cov
	@echo "✅ All CI checks passed!"
