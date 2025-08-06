"""
Django management command to create test data for development.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create test data for development - users, campaigns, characters, etc."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=2,
            help="Number of additional test users to create (default: 2)",
        )
        parser.add_argument(
            "--campaigns",
            type=int,
            default=1,
            help="Number of additional test campaigns to create (default: 1)",
        )
        parser.add_argument(
            "--characters",
            type=int,
            default=3,
            help="Number of test characters to create (default: 3)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing test data before creating new data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating it",
        )

    def handle(self, *args, **options):
        """Create test data."""
        users_count = options["users"]
        campaigns_count = options["campaigns"]
        characters_count = options["characters"]
        clear_data = options["clear"]
        dry_run = options["dry_run"]
        verbosity = options["verbosity"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN: Would create test data with:")
            )
            self.stdout.write(f"  👥 Users: {users_count + 2} (includes testuser and gm_user)")
            self.stdout.write(f"  🎲 Campaigns: {campaigns_count + 1} (includes Test Campaign)")
            self.stdout.write(f"  🎭 Characters: {characters_count}")
            self.stdout.write(self.style.SUCCESS("✅ Dry run completed!"))
            return

        try:
            if clear_data:
                if verbosity >= 1:
                    self.stdout.write("Clearing existing test data...")
                self.clear_test_data()

            if verbosity >= 1:
                self.stdout.write("Creating test data...")

            # Create test users
            test_users = self.create_test_users(users_count, verbosity)
            
            # Create test campaigns (when campaign models are implemented)
            test_campaigns = self.create_test_campaigns(campaigns_count, verbosity)
            
            # Create test characters (when character models are implemented)
            test_characters = self.create_test_characters(characters_count, verbosity)

            self.stdout.write(
                self.style.SUCCESS("✅ Test data created successfully!")
            )
            self.stdout.write(f"  👥 Created {len(test_users)} users")
            self.stdout.write(f"  🎲 Created {len(test_campaigns)} campaigns")
            self.stdout.write(f"  🎭 Created {len(test_characters)} characters")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to create test data: {e}")
            )
            exit(1)

    def clear_test_data(self):
        """Clear existing test data."""
        # Clear test users (keep superusers)
        User.objects.filter(
            username__in=['testuser', 'gm_user']
        ).delete()
        
        User.objects.filter(
            username__startswith='testuser_',
            is_superuser=False
        ).delete()

        # Clear test campaigns when models are implemented
        try:
            from campaigns.models import Campaign
            Campaign.objects.filter(name__startswith='Test Campaign').delete()
        except (ImportError, AttributeError):
            # Campaign model not implemented yet
            pass

        # Clear test characters when models are implemented
        try:
            from characters.models import Character
            Character.objects.filter(name__startswith='Test Character').delete()
        except (ImportError, AttributeError):
            # Character model not implemented yet
            pass

    def create_test_users(self, count, verbosity):
        """Create test users."""
        if verbosity >= 2:
            self.stdout.write("Creating test users...")

        users = []

        # Create default test users
        default_users = [
            {
                'username': 'testuser',
                'email': 'testuser@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'password': 'testpass123'
            },
            {
                'username': 'gm_user',
                'email': 'gm@example.com',
                'first_name': 'Game',
                'last_name': 'Master',
                'password': 'gmpass123'
            }
        ]

        for user_data in default_users:
            if not User.objects.filter(username=user_data['username']).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )
                users.append(user)
                if verbosity >= 2:
                    self.stdout.write(f"  Created user: {user.username}")

        # Create additional test users
        for i in range(1, count + 1):
            username = f'testuser_{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'testuser{i}@example.com',
                    password=f'testpass{i}123',
                    first_name=f'Test{i}',
                    last_name='User'
                )
                users.append(user)
                if verbosity >= 2:
                    self.stdout.write(f"  Created user: {user.username}")

        return users

    def create_test_campaigns(self, count, verbosity):
        """Create test campaigns."""
        if verbosity >= 2:
            self.stdout.write("Creating test campaigns...")

        campaigns = []

        try:
            from campaigns.models import Campaign

            # Create default test campaign
            if not Campaign.objects.filter(name='Test Campaign').exists():
                campaign = Campaign.objects.create(
                    name='Test Campaign',
                    description='A test campaign for development',
                    game_system='wod'  # Assuming World of Darkness as default
                )
                campaigns.append(campaign)
                if verbosity >= 2:
                    self.stdout.write(f"  Created campaign: {campaign.name}")

            # Create additional test campaigns
            for i in range(1, count + 1):
                campaign_name = f'Test Campaign {i}'
                if not Campaign.objects.filter(name=campaign_name).exists():
                    campaign = Campaign.objects.create(
                        name=campaign_name,
                        description=f'Test campaign #{i} for development',
                        game_system='wod'
                    )
                    campaigns.append(campaign)
                    if verbosity >= 2:
                        self.stdout.write(f"  Created campaign: {campaign.name}")

        except (ImportError, AttributeError):
            # Campaign model not implemented yet
            if verbosity >= 2:
                self.stdout.write("  Campaign model not implemented yet, skipping...")

        return campaigns

    def create_test_characters(self, count, verbosity):
        """Create test characters."""
        if verbosity >= 2:
            self.stdout.write("Creating test characters...")

        characters = []

        try:
            from characters.models import Character

            # Create test characters
            for i in range(1, count + 1):
                character_name = f'Test Character {i}'
                if not Character.objects.filter(name=character_name).exists():
                    character = Character.objects.create(
                        name=character_name,
                        description=f'Test character #{i} for development'
                    )
                    characters.append(character)
                    if verbosity >= 2:
                        self.stdout.write(f"  Created character: {character.name}")

        except (ImportError, AttributeError):
            # Character model not implemented yet
            if verbosity >= 2:
                self.stdout.write("  Character model not implemented yet, skipping...")

        return characters