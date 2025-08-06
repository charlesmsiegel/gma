import os
import sys
import django
import pytest


class TestDjangoProjectSetup:
    """Test that Django project is properly configured."""

    def test_django_project_exists(self):
        """Test that Django project directory exists."""
        assert os.path.exists(
            "gm_app"
        ), "Django project 'gm_app' directory should exist"
        assert os.path.exists(
            "gm_app/settings.py"
        ), "settings.py should exist in gm_app"
        assert os.path.exists("gm_app/urls.py"), "urls.py should exist in gm_app"
        assert os.path.exists("gm_app/wsgi.py"), "wsgi.py should exist in gm_app"
        assert os.path.exists("gm_app/asgi.py"), "asgi.py should exist in gm_app"

    def test_manage_py_exists(self):
        """Test that manage.py exists at project root."""
        assert os.path.exists("manage.py"), "manage.py should exist at project root"

    def test_postgresql_configured(self):
        """Test that PostgreSQL is configured as the database backend."""
        # Add project to path to import settings
        sys.path.insert(0, os.path.abspath("."))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gm_app.settings")
        django.setup()

        from django.conf import settings

        assert "default" in settings.DATABASES, "Default database should be configured"
        assert (
            settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
        ), "PostgreSQL should be configured as database backend"

    def test_redis_sessions_configured(self):
        """Test that Redis is configured for session storage."""
        from django.conf import settings

        assert hasattr(
            settings, "SESSION_ENGINE"
        ), "SESSION_ENGINE should be configured"
        assert (
            settings.SESSION_ENGINE == "django.contrib.sessions.backends.cache"
        ), "Sessions should use cache backend"
        assert hasattr(
            settings, "SESSION_CACHE_ALIAS"
        ), "SESSION_CACHE_ALIAS should be configured"
        assert (
            settings.SESSION_CACHE_ALIAS == "default"
        ), "Session cache should use default alias"

        # Check Redis cache configuration
        assert "default" in settings.CACHES, "Default cache should be configured"
        assert (
            settings.CACHES["default"]["BACKEND"]
            == "django.core.cache.backends.redis.RedisCache"
        ), "Redis should be configured as cache backend"

    def test_logging_configured(self):
        """Test that basic logging is configured."""
        from django.conf import settings

        assert hasattr(settings, "LOGGING"), "LOGGING should be configured"
        assert "version" in settings.LOGGING, "Logging config should have version"
        assert "handlers" in settings.LOGGING, "Logging config should have handlers"
        assert "loggers" in settings.LOGGING, "Logging config should have loggers"

    def test_gitignore_exists(self):
        """Test that .gitignore file exists with Django patterns."""
        assert os.path.exists(".gitignore"), ".gitignore file should exist"

        with open(".gitignore", "r") as f:
            content = f.read()
            # Check for common Django patterns
            assert (
                "*.pyc" in content or "__pycache__" in content
            ), ".gitignore should include Python bytecode patterns"
            assert "db.sqlite3" in content, ".gitignore should include SQLite database"
            assert "*.log" in content, ".gitignore should include log files"
            assert (
                ".env" in content or "local_settings.py" in content
            ), ".gitignore should include environment/local settings"

    def test_environment_yml_exists(self):
        """Test that environment.yml exists with necessary packages."""
        assert os.path.exists("environment.yml"), "environment.yml should exist"

        with open("environment.yml", "r") as f:
            content = f.read().lower()
            assert "django" in content, "environment.yml should include Django"
            assert (
                "psycopg2" in content
            ), "environment.yml should include PostgreSQL adapter"
            assert "redis" in content, "environment.yml should include Redis"
