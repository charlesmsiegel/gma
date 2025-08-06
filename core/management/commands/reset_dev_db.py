"""
Django management command to reset development database.
"""

import sys
from getpass import getpass

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reset development database - drops all data, runs migrations, and optionally creates superuser"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )
        parser.add_argument(
            "--no-superuser",
            action="store_true",
            help="Skip superuser creation",
        )

    def handle(self, *args, **options):
        """Reset the development database."""
        force = options["force"]
        create_superuser = not options["no_superuser"]

        if not force:
            self.stdout.write(
                self.style.WARNING("⚠️  WARNING: This will delete ALL data in the database!")
            )
            confirm = input("Are you sure you want to continue? (yes/no): ").lower()
            
            if confirm not in ["yes", "y"]:
                self.stdout.write(self.style.ERROR("❌ Operation cancelled"))
                return

        try:
            # Flush database (delete all data)
            self.stdout.write("Flushing database...")
            call_command("flush", "--noinput")
            self.stdout.write(self.style.SUCCESS("  ✅ Database flushed"))

            # Run migrations
            self.stdout.write("Running migrations...")
            call_command("migrate")
            self.stdout.write(self.style.SUCCESS("  ✅ Migrations completed"))

            # Create superuser if requested
            if create_superuser:
                self.create_superuser()

            self.stdout.write(
                self.style.SUCCESS("✅ Database reset completed successfully!")
            )

        except Exception as e:
            if "flush" in str(e).lower() or "database" in str(e).lower():
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to flush database: {e}")
                )
            elif "migrat" in str(e).lower():
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to run migrations: {e}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Database reset failed: {e}")
                )
            sys.exit(1)

    def create_superuser(self):
        """Create a superuser account."""
        self.stdout.write("Creating superuser account...")
        
        try:
            # Check if any superuser already exists
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write(
                    self.style.WARNING("  ⚠️  Superuser already exists, skipping creation")
                )
                return

            # Get superuser details
            username = input("Enter superuser username (default: admin): ").strip() or "admin"
            email = input("Enter superuser email: ").strip()
            
            while not email:
                email = input("Email is required. Enter superuser email: ").strip()
            
            password = getpass("Enter superuser password: ").strip()
            
            while not password:
                password = getpass("Password is required. Enter superuser password: ").strip()

            # Create superuser
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Superuser '{username}' created successfully")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ❌ Failed to create superuser: {e}")
            )
            # Don't exit here, as database reset was successful