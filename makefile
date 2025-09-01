# Grid Enforcer Development Makefile - Enhanced Version

.PHONY: help setup dev-up dev-down test lint format check install clean
.PHONY: test-performance test-integration test-all prod-up prod-down
.PHONY: security-scan backup restore monitor logs

# Default target
help:
	@echo "Grid Enforcer Development Commands:"
	@echo ""
	@echo "Setup & Environment:"
	@echo "  make setup           - Set up development environment"
	@echo "  make install         - Install dependencies in venv"
	@echo "  make clean          - Clean up containers and volumes"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up         - Start development services"
	@echo "  make dev-down       - Stop development services"
	@echo "  make format         - Format code"
	@echo "  make lint           - Run linting checks"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run basic tests"
	@echo "  make test-local     - Run tests locally (with venv)"
	@echo "  make test-coverage  - Run tests with coverage"
	@echo "  make test-performance - Run performance tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-all       - Run all test suites"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up        - Start production environment"
	@echo "  make prod-down      - Stop production environment"
	@echo "  make backup         - Backup production data"
	@echo "  make restore        - Restore from backup"
	@echo ""
	@echo "Monitoring & Security:"
	@echo "  make security-scan  - Run security vulnerability scan"
	@echo "  make monitor        - Start monitoring stack"
	@echo "  make logs          - View service logs"
	@echo "  make health-check  - Check service health"

# Set up development environment
setup:
	@echo "Setting up development environment..."
	@which python3 >/dev/null 2>&1 && PYTHON=python3 || PYTHON=python; \
	$PYTHON -m venv venv
	@echo "Virtual environment created"
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Development environment ready. Activate with: source venv/bin/activate"

# Start development services
dev-up:
	docker compose up -d

# Start with full development tools
dev-up-full:
	docker compose --profile dev --profile mqtt --profile database up -d

# Stop development services
dev-down:
	docker compose down

# Install dependencies (use venv)
install:
	@which python3 >/dev/null 2>&1 && PYTHON=python3 || PYTHON=python; \
	if [ ! -d "venv" ]; then $PYTHON -m venv venv; fi
	. venv/bin/activate && pip install -r requirements.txt

# Run tests using Docker
test:
	docker run --rm -v $(PWD):/app -w /app python:3.11-alpine sh -c "\
		pip install pytest pytest-asyncio pytest-mock && \
		PYTHONPATH=/app pytest tests/test_integration.py tests/test_pricecalculator.py -v"

# Run tests locally (with venv)
test-local:
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	. venv/bin/activate && PYTHONPATH=. pytest tests/ -v

# Run tests with coverage
test-coverage:
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	. venv/bin/activate && PYTHONPATH=. pytest tests/ -v --cov=custom_components/gridenforcer --cov-report=term-missing --cov-report=html

# Run performance tests
test-performance:
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	. venv/bin/activate && PYTHONPATH=. pytest tests/test_performance.py -v -s

# Run integration tests
test-integration:
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	. venv/bin/activate && PYTHONPATH=. pytest tests/test_components.py -v

# Run all test suites
test-all: test-local test-performance test-integration
	@echo "✅ All test suites completed"

# Format code locally (with venv)
format:
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	. venv/bin/activate && isort --profile black custom_components/
	. venv/bin/activate && black custom_components/
	@echo "✅ Code formatted successfully"

# Run linting checks locally (with venv)
lint:
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	. venv/bin/activate && isort --profile black --check-only custom_components/
	. venv/bin/activate && black --check custom_components/

# Alternative: Use dev-tools container for quality checks
check-docker:
	docker compose --profile dev up -d dev-tools
	docker exec ge-dev-tools sh -c "\
		pip install black isort pytest homeassistant && \
		black --check custom_components/ && \
		isort --check-only custom_components/ && \
		pytest tests/ -v"

# Format using dev-tools container
format-docker:
	docker compose --profile dev up -d dev-tools
	docker exec ge-dev-tools sh -c "\
		pip install black isort && \
		black custom_components/ && \
		isort custom_components/"

# Production Commands
prod-up:
	@echo "🚀 Starting production environment..."
	docker compose -f docker-compose.prod.yml up -d
	@echo "✅ Production services started"
	@echo "📊 Monitor status: make monitor"

prod-down:
	@echo "🛑 Stopping production environment..."
	docker compose -f docker-compose.prod.yml down
	@echo "✅ Production services stopped"

# Start production with monitoring
prod-up-monitoring:
	docker compose -f docker-compose.prod.yml --profile monitoring up -d

# Security scan using Trivy
security-scan:
	@echo "🔒 Running security vulnerability scan..."
	docker run --rm -v $(PWD):/app aquasec/trivy:latest fs --exit-code 1 /app
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy:latest image gridenforcer-ha-prod:latest

# Backup production data
backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@timestamp=$(date +%Y%m%d_%H%M%S); \
	docker compose -f docker-compose.prod.yml exec -T mariadb \
		mysqldump -u root -p$(cat secrets/db_root_password.txt) homeassistant \
		> backups/db_backup_$timestamp.sql
	@docker run --rm -v gridenforcer_ha_config:/source -v $(PWD)/backups:/backup \
		alpine tar czf /backup/ha_config_$timestamp.tar.gz -C /source .
	@echo "✅ Backup completed: backups/backup_$timestamp.*"

# Restore from backup (requires backup file argument)
restore:
	@if [ -z "$(BACKUP)" ]; then \
		echo "❌ Please specify backup file: make restore BACKUP=backups/db_backup_20240101_120000.sql"; \
		exit 1; \
	fi
	@echo "🔄 Restoring from backup: $(BACKUP)"
	@docker compose -f docker-compose.prod.yml exec -T mariadb \
		mysql -u root -p$(cat secrets/db_root_password.txt) homeassistant < $(BACKUP)
	@echo "✅ Database restored from $(BACKUP)"

# Monitor services
monitor:
	@echo "📊 Service Status:"
	@docker compose -f docker-compose.prod.yml ps
	@echo ""
	@echo "🏥 Health Checks:"
	@docker inspect gridenforcer-ha-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "❌ Home Assistant: Not running"
	@docker inspect gridenforcer-db-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "❌ Database: Not running"
	@docker inspect gridenforcer-mqtt-prod --format='{{.State.Health.Status}}' 2>/dev/null || echo "❌ MQTT: Not running"

# View logs
logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=50

# View specific service logs
logs-ha:
	docker compose -f docker-compose.prod.yml logs -f home-assistant

logs-db:
	docker compose -f docker-compose.prod.yml logs -f mariadb

logs-mqtt:
	docker compose -f docker-compose.prod.yml logs -f mosquitto

# Health check all services
health-check:
	@echo "🏥 Comprehensive Health Check:"
	@echo "═══════════════════════════════"
	
	@echo "📱 Home Assistant:"
	@curl -s -f http://localhost:8123/ >/dev/null && echo "  ✅ Web interface accessible" || echo "  ❌ Web interface failed"
	@curl -s -f http://localhost:8123/api/ >/dev/null 2>&1 || echo "  ⚠️  API requires authentication (expected)"
	
	@echo "🗄️  Database:"
	@docker exec gridenforcer-db-prod mysqladmin ping -h localhost -u root -p$(cat secrets/db_root_password.txt 2>/dev/null || echo "password") 2>/dev/null && echo "  ✅ Database responding" || echo "  ❌ Database failed"
	
	@echo "📡 MQTT Broker:"
	@timeout 5 docker exec gridenforcer-mqtt-prod mosquitto_pub -h localhost -t "health/check" -m "test" 2>/dev/null && echo "  ✅ MQTT broker responding" || echo "  ❌ MQTT broker failed"
	
	@echo "💾 Disk Space:"
	@df -h | grep -E "(Filesystem|/$)" | head -2
	
	@echo "🐳 Docker Resources:"
	@docker system df

# Clean up Docker resources
clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker compose down -v
	docker compose -f docker-compose.prod.yml down -v
	docker system prune -f
	@echo "✅ Cleanup completed"

# Deep clean (removes everything including images)
clean-all:
	@echo "🗑️  Deep cleaning (WARNING: removes all Docker data)..."
	@read -p "Are you sure? This will remove all containers, images, and volumes [y/N]: " confirm && \
	if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then \
		docker compose down -v; \
		docker compose -f docker-compose.prod.yml down -v; \
		docker system prune -a -f --volumes; \
		echo "✅ Deep clean completed"; \
	else \
		echo "❌ Deep clean cancelled"; \
	fi

# Test the CI/CD pipeline locally
ci-test:
	@echo "🧪 Testing CI/CD pipeline steps locally..."
	make lint
	make test
	docker build -t ge-test .
	@echo "✅ CI/CD test completed successfully!"

# Quick development cycle
dev-cycle: format lint test-local
	@echo "🔄 Development cycle completed successfully!"

# Pre-commit hook setup
setup-hooks:
	@if [ ! -d "venv" ]; then echo "❌ Run 'make setup' first"; exit 1; fi
	. venv/bin/activate && pip install pre-commit
	. venv/bin/activate && pre-commit install
	@echo "✅ Pre-commit hooks installed"

# Generate documentation
docs:
	@echo "📚 Generating documentation..."
	@mkdir -p docs
	@echo "# GridEnforcer Integration Documentation" > docs/README.md
	@echo "" >> docs/README.md
	@echo "## Architecture Overview" >> docs/README.md
	@find custom_components/gridenforcer -name "*.py" -exec echo "### {}" \; -exec head -20 {} \; >> docs/README.md
	@echo "✅ Documentation generated in docs/"

# Performance benchmark
benchmark:
	@echo "⚡ Running performance benchmarks..."
	@if [ ! -d "venv" ]; then echo "❌ Run 'make setup' first"; exit 1; fi
	. venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_performance.py::test_price_calculator_performance -v -s
	. venv/bin/activate && PYTHONPATH=. python -m pytest tests/test_performance.py::test_integration_startup_time -v -s
	@echo "✅ Benchmark completed"