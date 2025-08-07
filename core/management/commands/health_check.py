"""
Django management command to test database and Redis connections.
"""

from django.core.cache import caches
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Test database and Redis connections to verify configuration"

    def handle(self, *args, **options):
        """Run health checks for database and Redis."""
        success = True

        # Test database
        try:
            connections["default"].ensure_connection()
            self.stdout.write(self.style.SUCCESS("✅ Database connection: OK"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Database connection failed: {e}"))
            success = False

        # Test Redis cache
        try:
            cache = caches["default"]
            cache.set("health_check", "ok", 1)
            result = cache.get("health_check")
            if result == "ok":
                self.stdout.write(self.style.SUCCESS("✅ Redis connection: OK"))
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Redis connection failed: Cache test failed")
                )
                success = False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Redis connection failed: {e}"))
            success = False

        if success:
            self.stdout.write(self.style.SUCCESS("\n✅ All services OK"))
        else:
            self.stdout.write(self.style.ERROR("\n❌ Health check failed"))
            exit(1)
