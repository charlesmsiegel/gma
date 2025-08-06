.PHONY: help runserver start-postgres start-redis stop-postgres stop-redis setup-env migrate clean health-check test test-coverage

# Environment paths
GMA_ENV_PATH = /home/janothar/miniconda3/envs/gma
PG_BIN = $(GMA_ENV_PATH)/bin
PG_DATA = $(GMA_ENV_PATH)/var/postgres

help:
	@echo "Available commands:"
	@echo "  runserver      - Start PostgreSQL, Redis, and Django development server on port 8080"
	@echo "  start-postgres - Start PostgreSQL server"
	@echo "  start-redis    - Start Redis server"
	@echo "  stop-postgres  - Stop PostgreSQL server"
	@echo "  stop-redis     - Stop Redis server"
	@echo "  setup-env      - Create conda environment from environment.yml"
	@echo "  migrate        - Run Django migrations"
	@echo "  health-check   - Test database and Redis connections"
	@echo "  test           - Run all tests"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  clean          - Stop all services"

runserver: start-postgres start-redis migrate
	@echo "Starting Django development server on port 8080..."
	$(GMA_ENV_PATH)/bin/python manage.py runserver 0.0.0.0:8080

start-postgres:
	@echo "Starting PostgreSQL..."
	@if ! $(PG_BIN)/pg_isready -q 2>/dev/null; then \
		echo "PostgreSQL not running, starting..."; \
		if [ ! -d "$(PG_DATA)" ]; then \
			echo "Initializing PostgreSQL database..."; \
			$(PG_BIN)/initdb -D $(PG_DATA); \
		fi; \
		$(PG_BIN)/pg_ctl start -D $(PG_DATA) -l $(PG_DATA)/server.log; \
		sleep 3; \
		echo "Creating database and user..."; \
		$(PG_BIN)/createdb gm_app_db 2>/dev/null || true; \
		$(PG_BIN)/psql -d postgres -c "CREATE USER postgres WITH SUPERUSER PASSWORD 'postgres';" 2>/dev/null || true; \
		$(PG_BIN)/psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE gm_app_db TO postgres;" 2>/dev/null || true; \
	else \
		echo "PostgreSQL already running"; \
	fi

start-redis:
	@echo "Starting Redis..."
	@if ! $(GMA_ENV_PATH)/bin/redis-cli ping > /dev/null 2>&1; then \
		echo "Redis not running, starting..."; \
		$(GMA_ENV_PATH)/bin/redis-server --daemonize yes --port 6379; \
		sleep 1; \
	else \
		echo "Redis already running"; \
	fi

stop-postgres:
	@echo "Stopping PostgreSQL..."
	@$(PG_BIN)/pg_ctl stop -D $(PG_DATA) || true

stop-redis:
	@echo "Stopping Redis..."
	@$(GMA_ENV_PATH)/bin/redis-cli shutdown || true

setup-env:
	@echo "Creating conda environment..."
	conda env create -f environment.yml

migrate:
	@echo "Running Django migrations..."
	$(GMA_ENV_PATH)/bin/python manage.py migrate

health-check: start-postgres start-redis
	@echo "Running health checks..."
	$(GMA_ENV_PATH)/bin/python manage.py health_check
	@echo "Testing dbshell access..."
	@echo "SELECT 'Database shell access: OK' as test;" | PATH="$(PG_BIN):$$PATH" $(GMA_ENV_PATH)/bin/python manage.py dbshell

test:
	@echo "Running all tests..."
	$(GMA_ENV_PATH)/bin/python manage.py test

test-coverage:
	@echo "Running tests with coverage..."
	$(GMA_ENV_PATH)/bin/python -m coverage run manage.py test
	$(GMA_ENV_PATH)/bin/python -m coverage combine
	$(GMA_ENV_PATH)/bin/python -m coverage report --precision=2 --show-missing --skip-covered
	$(GMA_ENV_PATH)/bin/python -m coverage html
	@echo "HTML coverage report generated at htmlcov/index.html"
	$(GMA_ENV_PATH)/bin/python -m coverage report --fail-under=80

clean: stop-postgres stop-redis
	@echo "All services stopped"