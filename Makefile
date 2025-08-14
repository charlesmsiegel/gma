.PHONY: help runserver runserver-django start-postgres start-redis stop-postgres stop-redis setup-env migrate clean health-check test test-coverage start-frontend build-frontend stop-all check-frontend reset-migrations create-superuser reset-dev pristine

# Environment paths
GMA_ENV_PATH = /home/janothar/miniconda3/envs/gma
PG_BIN = $(GMA_ENV_PATH)/bin
PG_DATA = $(GMA_ENV_PATH)/var/postgres

help:
	@echo "Available commands:"
	@echo "  runserver      - Start ALL services: PostgreSQL, Redis, Django (8080), and React (3000)"
	@echo "  runserver-django - Start only Django server with PostgreSQL and Redis"
	@echo "  start-frontend - Start React development server on port 3000"
	@echo "  build-frontend - Build React app for production"
	@echo "  start-postgres - Start PostgreSQL server"
	@echo "  start-redis    - Start Redis server"
	@echo "  stop-postgres  - Stop PostgreSQL server"
	@echo "  stop-redis     - Stop Redis server"
	@echo "  setup-env      - Create conda environment from environment.yml"
	@echo "  migrate        - Run Django migrations"
	@echo "  reset-migrations - Drop database, delete migrations, recreate everything"
	@echo "  create-superuser - Create Django admin superuser"
	@echo "  reset-dev      - Complete dev reset: migrations + superuser (interactive)"
	@echo "  pristine       - NUCLEAR OPTION: Clean everything to pristine state"
	@echo "  health-check   - Test database and Redis connections"
	@echo "  test           - Run all tests"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  stop-all       - Stop all services (PostgreSQL, Redis)"
	@echo "  clean          - Alias for stop-all"

runserver: start-postgres start-redis migrate check-frontend
	@PATH="$(GMA_ENV_PATH)/bin:$$PATH" ./scripts/run-dev-servers.sh

runserver-django: start-postgres start-redis migrate
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
	@$(PG_BIN)/pg_ctl stop -D $(PG_DATA) 2>/dev/null || echo "PostgreSQL already stopped"

stop-redis:
	@echo "Stopping Redis..."
	@$(GMA_ENV_PATH)/bin/redis-cli shutdown 2>/dev/null || echo "Redis already stopped"

setup-env:
	@echo "Creating conda environment..."
	conda env create -f environment.yml

migrate:
	@echo "Running Django migrations..."
	$(GMA_ENV_PATH)/bin/python manage.py migrate

reset-migrations: start-postgres start-redis
	@echo "⚠️  RESETTING ALL MIGRATIONS & DATABASE ⚠️"
	@echo "This will:"
	@echo "  - Drop and recreate the database"
	@echo "  - Delete all migration files"
	@echo "  - Create fresh migrations"
	@echo "  - Apply migrations to clean database"
	@echo "Make sure you have backed up any important data!"
	@echo ""
	@read -p "Are you sure you want to continue? (y/N): " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || (echo "Cancelled." && exit 1)
	@echo ""
	@echo "🗑️  Dropping and recreating database..."
	@$(PG_BIN)/dropdb gm_app_db 2>/dev/null || true
	@$(PG_BIN)/createdb gm_app_db
	@$(PG_BIN)/psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE gm_app_db TO postgres;" 2>/dev/null || true
	@echo "✅ Database recreated"
	@echo ""
	@echo "🗑️  Deleting migration files..."
	@find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	@find . -path "*/migrations/*.pyc" -delete
	@echo "✅ Migration files deleted"
	@echo ""
	@echo "📝 Creating new migrations..."
	@$(GMA_ENV_PATH)/bin/python manage.py makemigrations
	@echo "✅ New migrations created"
	@echo ""
	@echo "🔄 Applying migrations to clean database..."
	@$(GMA_ENV_PATH)/bin/python manage.py migrate
	@echo "✅ Migrations applied successfully"
	@echo ""
	@echo "🎉 Migration reset complete!"
	@echo "💡 Don't forget to create a superuser: make create-superuser"

create-superuser: start-postgres start-redis
	@echo "Creating Django superuser..."
	@$(GMA_ENV_PATH)/bin/python manage.py createsuperuser

reset-dev: reset-migrations
	@echo ""
	@echo "🔧 Would you like to create a superuser now? (y/N):"
	@read -p "> " create_user && [ "$$create_user" = "y" ] || [ "$$create_user" = "Y" ] && $(MAKE) create-superuser || echo "Skipping superuser creation"
	@echo ""
	@echo "🚀 Development environment is ready!"
	@echo "👉 Run 'make runserver' to start the application"

health-check: start-postgres start-redis
	@echo "Running health checks..."
	$(GMA_ENV_PATH)/bin/python manage.py health_check
	@echo "Testing dbshell access..."
	@echo "SELECT 'Database shell access: OK' as test;" | PATH="$(PG_BIN):$$PATH" $(GMA_ENV_PATH)/bin/python manage.py dbshell

test:
	@echo "Running all tests..."
	$(GMA_ENV_PATH)/bin/python manage.py test --settings=gm_app.test_settings

test-coverage:
	@echo "Running tests with coverage..."
	$(GMA_ENV_PATH)/bin/python -m coverage run manage.py test --settings=gm_app.test_settings
	$(GMA_ENV_PATH)/bin/python -m coverage combine
	$(GMA_ENV_PATH)/bin/python -m coverage report --precision=2 --show-missing --skip-covered
	$(GMA_ENV_PATH)/bin/python -m coverage html
	@echo "HTML coverage report generated at htmlcov/index.html"
	$(GMA_ENV_PATH)/bin/python -m coverage report --fail-under=80

start-frontend:
	@echo "Starting React development server on port 3000..."
	@cd frontend && npm start

build-frontend:
	@echo "Building React app for production..."
	@cd frontend && npm run build:django

check-frontend:
	@echo "Checking frontend dependencies..."
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	else \
		echo "Frontend dependencies already installed"; \
	fi

stop-all:
	@echo "Stopping all services..."
	@# Stop PostgreSQL
	@$(PG_BIN)/pg_ctl stop -D $(PG_DATA) 2>/dev/null || echo "PostgreSQL already stopped"
	@# Stop Redis
	@$(GMA_ENV_PATH)/bin/redis-cli shutdown 2>/dev/null || echo "Redis already stopped"
	@# Kill any running React development servers
	@-pkill -f "react-scripts start" 2>/dev/null || true
	@-pkill -f "npm start" 2>/dev/null || true
	@echo "All services stopped"

clean: stop-all

pristine:
	@echo "☢️  NUCLEAR OPTION: CREATING PRISTINE STATE ☢️"
	@echo "This will DESTROY everything and create a completely clean state:"
	@echo "  🗑️  Drop and recreate database"
	@echo "  🗑️  Delete ALL migration files"
	@echo "  🗑️  Delete ALL __pycache__ directories"
	@echo "  🗑️  Delete ALL .pyc files"
	@echo "  🗑️  Remove empty directories"
	@echo "  🗑️  Clean coverage reports"
	@echo "  🗑️  Clean frontend build artifacts"
	@echo ""
	@echo "⚠️  THIS CANNOT BE UNDONE ⚠️"
	@echo "Make sure you have committed any important changes!"
	@echo ""
	@read -p "Type 'YES' to proceed with nuclear cleanup: " confirm && [ "$$confirm" = "YES" ] || (echo "❌ Cancelled." && exit 1)
	@echo ""
	@echo "🧹 Starting pristine cleanup..."
	@echo ""
	@echo "🗑️  Stopping services..."
	@-$(PG_BIN)/pg_ctl stop -D $(PG_DATA) 2>/dev/null || echo "PostgreSQL already stopped"
	@-$(GMA_ENV_PATH)/bin/redis-cli shutdown 2>/dev/null || echo "Redis already stopped"
	@-pkill -f "react-scripts start" 2>/dev/null || true
	@-pkill -f "npm start" 2>/dev/null || true
	@echo "✅ Services stopped"
	@echo ""
	@echo "🗑️  Dropping database..."
	@-$(PG_BIN)/dropdb gm_app_db 2>/dev/null || echo "Database already dropped or PostgreSQL not running"
	@echo "✅ Database dropped"
	@echo ""
	@echo "🗑️  Deleting all migration files..."
	@find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	@find . -path "*/migrations/*.pyc" -delete
	@echo "✅ Migration files deleted"
	@echo ""
	@echo "🗑️  Deleting all __pycache__ directories..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ __pycache__ directories deleted"
	@echo ""
	@echo "🗑️  Deleting all .pyc files..."
	@find . -name "*.pyc" -delete
	@echo "✅ .pyc files deleted"
	@echo ""
	@echo "🗑️  Removing empty directories..."
	@# Remove empty directories multiple times to handle nested empties
	@for i in 1 2 3 4 5; do \
		empty_count=$$(find . -type d -empty -not -path "*/.git/*" -not -path "./OLD_CODE/*" | wc -l); \
		if [ $$empty_count -eq 0 ]; then break; fi; \
		find . -type d -empty -not -path "*/.git/*" -not -path "./OLD_CODE/*" -delete 2>/dev/null || true; \
	done
	@echo "✅ Empty directories removed"
	@echo ""
	@echo "🗑️  Cleaning coverage reports..."
	@rm -rf htmlcov/ .coverage .coverage.* 2>/dev/null || true
	@echo "✅ Coverage reports cleaned"
	@echo ""
	@echo "🗑️  Cleaning frontend artifacts..."
	@rm -rf frontend/build/ frontend/.cache/ 2>/dev/null || true
	@echo "✅ Frontend artifacts cleaned"
	@echo ""
	@echo "🗑️  Cleaning test artifacts..."
	@rm -rf .pytest_cache/ 2>/dev/null || true
	@echo "✅ Test artifacts cleaned"
	@echo ""
	@echo "🎉 PRISTINE STATE ACHIEVED! 🎉"
	@echo ""
	@echo "🔄 To get back to working state, run:"
	@echo "   make reset-dev    # Recreate DB, migrations, and superuser"
	@echo "   make runserver    # Start development environment"
