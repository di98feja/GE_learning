# Grid Enforcer Development Makefile

.PHONY: help setup dev-up dev-down test lint format check install clean

# Default target
help:
	@echo "Grid Enforcer Development Commands:"
	@echo "  make setup      - Set up development environment"
	@echo "  make dev-up     - Start development services"
	@echo "  make dev-down   - Stop development services"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting checks"
	@echo "  make format     - Format code"
	@echo "  make check      - Run all quality checks"
	@echo "  make install    - Install dependencies in venv"
	@echo "  make clean      - Clean up containers and volumes"

# Set up development environment
setup:
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Development environment ready. Activate with: source venv/bin/activate"

# Start development services
dev-up:
	docker-compose up -d

# Start with development tools
dev-up-full:
	docker-compose --profile dev --profile mqtt up -d

# Stop development services
dev-down:
	docker-compose down

# Install dependencies (use venv)
install:
	@if [ ! -d "venv" ]; then python -m venv venv; fi
	. venv/bin/activate && pip install -r requirements.txt

# Run tests using Docker
test:
	docker run --rm -v $(PWD):/app -w /app python:3.11-alpine sh -c "\
		pip install pytest homeassistant && \
		pytest tests/ -v"

# Run linting checks using Docker
lint:
	docker run --rm -v $(PWD):/app -w /app python:3.11-alpine sh -c "\
		pip install black isort mypy && \
		black --check custom_components/ && \
		isort --check-only custom_components/"

# Format code using Docker
format:
	docker run --rm -v $(PWD):/app -w /app python:3.11-alpine sh -c "\
		pip install black isort && \
		black custom_components/ && \
		isort custom_components/"

# Run all quality checks
check: lint test

# Alternative: Use dev-tools container for quality checks
check-docker:
	docker-compose --profile dev up -d dev-tools
	docker exec ge-dev-tools sh -c "\
		pip install black isort pytest homeassistant && \
		black --check custom_components/ && \
		isort --check-only custom_components/ && \
		pytest tests/ -v"

# Format using dev-tools container
format-docker:
	docker-compose --profile dev up -d dev-tools
	docker exec ge-dev-tools sh -c "\
		pip install black isort && \
		black custom_components/ && \
		isort custom_components/"

# Clean up Docker resources
clean:
	docker-compose down -v
	docker system prune -f

# Test the CI/CD pipeline locally
ci-test:
	@echo "Testing CI/CD pipeline steps locally..."
	make lint
	make test
	docker build -t ge-test .
	@echo "CI/CD test completed successfully!"