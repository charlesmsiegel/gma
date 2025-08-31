"""Test settings for Django project using SQLite."""

import warnings

from .settings import *  # noqa: F403,F401

# Suppress pkg_resources deprecation warnings from django-polymorphic during tests
# This is a third-party library issue - django-polymorphic uses pkg_resources
# to get its version number, which is deprecated. This will be fixed upstream.
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="polymorphic",
)

# Use SQLite for testing to avoid PostgreSQL dependency
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
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
    def __contains__(self, item: str) -> bool:
        return True

    def __getitem__(self, item: str) -> None:
        return None


MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
SECRET_KEY = "test-secret-key-for-tests-only"  # nosec
DEBUG = False

# Disable email verification for integration tests
EMAIL_VERIFICATION_REQUIRED = False

# Set login URL to our custom view
LOGIN_URL = "users:login"


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
