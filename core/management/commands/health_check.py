"""
Django management command to test database and Redis connections.
"""

import redis
from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand
from django.db import connections

from core.models import HealthCheckLog


class Command(BaseCommand):
    help = "Test database and Redis connections to verify configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            action="store_true",
            help="Test only database connection",
        )
        parser.add_argument(
            "--redis",
            action="store_true",
            help="Test only Redis connection",
        )
        parser.add_argument(
            "--log",
            action="store_true",
            help="Log results to database",
        )

    def handle(self, *args, **options):
        """Run health checks for database and/or Redis."""
        success = True

        if not options["redis"]:  # Test database unless --redis only
            success &= self.test_database(log=options["log"])

        if not options["database"]:  # Test Redis unless --database only
            success &= self.test_redis(log=options["log"])

        if success:
            self.stdout.write(self.style.SUCCESS("✅ All health checks passed!"))
        else:
            self.stdout.write(self.style.ERROR("❌ Some health checks failed!"))
            exit(1)

    def test_database(self, log=False):
        """Test PostgreSQL database connection."""
        self.stdout.write("Testing database connection...")

        try:
            # Test default database connection
            db_conn = connections["default"]
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

            if result == (1,):
                self.stdout.write(self.style.SUCCESS("  ✅ Database connection: OK"))

                # Display database info
                db_settings = settings.DATABASES["default"]
                self.stdout.write(f"  📊 Database: {db_settings['NAME']}")
                self.stdout.write(
                    f"  🏠 Host: {db_settings['HOST']}:{db_settings['PORT']}"
                )
                self.stdout.write(f"  👤 User: {db_settings['USER']}")

                if log:
                    HealthCheckLog.objects.create(
                        service="database",
                        status="success",
                        details=f"Connected to {db_settings['NAME']} at {db_settings['HOST']}:{db_settings['PORT']}",
                    )

                return True
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "  ❌ Database connection: Failed (unexpected result)"
                    )
                )
                if log:
                    HealthCheckLog.objects.create(
                        service="database",
                        status="failure",
                        details="Unexpected result from database query",
                    )
                return False

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ Database connection: Failed - {e}")
            )
            if log:
                HealthCheckLog.objects.create(
                    service="database", status="failure", details=str(e)
                )
            return False

    def test_redis(self, log=False):
        """Test Redis connection."""
        self.stdout.write("Testing Redis connection...")

        try:
            # Test Redis cache connection
            cache = caches["default"]
            test_key = "health_check_test"
            test_value = "ok"

            # Test write
            cache.set(test_key, test_value, timeout=10)

            # Test read
            cached_value = cache.get(test_key)

            if cached_value == test_value:
                # Clean up
                cache.delete(test_key)

                self.stdout.write(self.style.SUCCESS("  ✅ Redis connection: OK"))

                # Display Redis info
                cache_location = settings.CACHES["default"]["LOCATION"]
                self.stdout.write(f"  🔗 Location: {cache_location}")

                # Test direct Redis connection for more details
                try:
                    redis_url = cache_location.replace("redis://", "")
                    host_port = redis_url.split("/")[0]
                    if ":" in host_port:
                        host, port = host_port.split(":")
                    else:
                        host, port = host_port, 6379

                    r = redis.Redis(host=host, port=int(port), decode_responses=True)
                    info = r.info()
                    self.stdout.write(
                        f"  📊 Redis version: {info.get('redis_version', 'unknown')}"
                    )
                    self.stdout.write(
                        f"  💾 Used memory: {info.get('used_memory_human', 'unknown')}"
                    )

                except Exception:
                    pass  # Don't fail if we can't get Redis details

                if log:
                    HealthCheckLog.objects.create(
                        service="redis",
                        status="success",
                        details=f"Connected to {cache_location}",
                    )

                return True
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "  ❌ Redis connection: Failed (cache test failed)"
                    )
                )
                if log:
                    HealthCheckLog.objects.create(
                        service="redis", status="failure", details="Cache test failed"
                    )
                return False

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Redis connection: Failed - {e}"))
            if log:
                HealthCheckLog.objects.create(
                    service="redis", status="failure", details=str(e)
                )
            return False
