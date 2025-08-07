"""Test settings for Django project using SQLite."""

from .settings import *  # noqa: F403,F401

# Use SQLite for testing to avoid PostgreSQL dependency
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "timeout": 20,
            "isolation_level": None,
        },
        "TEST": {
            "SERIALIZE": True,
        },
    }
}

# Use in-memory channel layer for tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Use database sessions instead of Redis cache for tests
SESSION_ENGINE = "django.contrib.sessions.backends.db"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
SECRET_KEY = "test-secret-key-for-tests-only"
DEBUG = False

# Set login URL to our custom view
LOGIN_URL = "users:login"

# Force test database to be created in series to avoid SQLite locking
TEST_RUNNER = "django.test.runner.DiscoverRunner"
TEST_NON_SERIALIZED_APPS = []

# Additional SQLite-specific settings to prevent locking
if "sqlite" in DATABASES["default"]["ENGINE"]:
    # Set environment variable to improve SQLite behavior
    import os

    os.environ.setdefault("SQLITE_TMPDIR", "/tmp")

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "WARNING",
    },
}
