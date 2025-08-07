"""Custom test runner to handle SQLite locking issues."""

from django.db import connections
from django.test.runner import DiscoverRunner


class SQLiteSafeTestRunner(DiscoverRunner):
    """Test runner with SQLite-specific locking safeguards."""

    def setup_databases(self, **kwargs):
        """Setup test databases with SQLite-specific configuration."""
        result = super().setup_databases(**kwargs)

        # Configure SQLite connections after database creation
        for alias in connections.databases.keys():
            connection = connections[alias]
            if connection.vendor == "sqlite":
                # Configure SQLite connection for better locking behavior
                try:
                    connection.ensure_connection()
                    if hasattr(connection, "connection") and connection.connection:
                        connection.connection.execute("PRAGMA busy_timeout=30000")
                        connection.connection.execute("PRAGMA journal_mode=MEMORY")
                        connection.connection.execute("PRAGMA synchronous=OFF")
                        connection.connection.execute("PRAGMA locking_mode=EXCLUSIVE")
                except Exception:
                    # If pragma commands fail, continue silently
                    pass

        return result
