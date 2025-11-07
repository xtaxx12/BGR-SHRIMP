# Makefile for BGR-SHRIMP development tasks

.PHONY: help install test lint format type-check security clean run

# Default target
help:
	@echo "BGR-SHRIMP Bot - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install all dependencies"
	@echo "  make install-dev    Install dev dependencies"
	@echo "  make setup-hooks    Setup pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-int       Run integration tests only"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make test-watch     Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (black + isort)"
	@echo "  make type-check     Run type checker (mypy)"
	@echo "  make security       Run security scanners"
	@echo "  make quality        Run all quality checks"
	@echo ""
	@echo "Running:"
	@echo "  make run            Run the application"
	@echo "  make dev            Run in development mode"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove cache and generated files"
	@echo "  make clean-all      Deep clean including dependencies"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Testing
test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-int:
	pytest tests/integration/ -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "📊 Coverage report generated: htmlcov/index.html"

test-watch:
	pytest-watch

test-fast:
	pytest -x --ff

# Code Quality
lint:
	ruff check app/

lint-fix:
	ruff check app/ --fix

format:
	black app/ tests/
	isort app/ tests/

type-check:
	mypy app/ --config-file=mypy.ini

security:
	@echo "🔍 Running security scans..."
	bandit -r app/ -ll
	safety check

quality: lint type-check
	@echo "✅ Code quality checks passed"

# Running
run:
	python start.py

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/
	rm -rf build/ dist/

clean-all: clean
	rm -rf venv/ .venv/

# Docker (if needed)
docker-build:
	docker build -t bgr-shrimp-bot .

docker-run:
	docker run -p 8000:8000 --env-file .env bgr-shrimp-bot

# Database/Data
reload-data:
	curl -X POST http://localhost:8000/webhook/reload-data \
		-H "Authorization: Bearer ${ADMIN_API_TOKEN}"

# Git helpers
commit-check:
	pre-commit run --all-files

# Documentation
docs:
	@echo "📚 Opening documentation..."
	@echo "README: file://$(PWD)/README.md"
	@echo "Tests: file://$(PWD)/tests/README.md"

# Health check
health:
	curl http://localhost:8000/health

# Quick start for new developers
quickstart: install-dev setup-hooks
	@echo ""
	@echo "🚀 Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy .env.example to .env and configure"
	@echo "2. Run 'make test' to verify setup"
	@echo "3. Run 'make dev' to start development server"
	@echo "4. Check 'make help' for more commands"