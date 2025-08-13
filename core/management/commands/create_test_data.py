"""
Django management command to create test data for development.
"""

import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


# Default counts for built-in test data
DEFAULT_USERS_COUNT = 2  # testuser and gm_user
DEFAULT_CAMPAIGNS_COUNT = 1  # Test Campaign
DEFAULT_CHARACTERS_COUNT = 0  # No built-in test characters

# Default test data names
DEFAULT_TEST_USERNAME = "testuser"
DEFAULT_GM_USERNAME = "gm_user"
DEFAULT_CAMPAIGN_NAME = "Test Campaign"
ADDITIONAL_USER_PREFIX = "testuser_"
ADDITIONAL_CHARACTER_PREFIX = "Test Character "


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
            self.stdout.write(
                f"  👥 Users: {users_count + DEFAULT_USERS_COUNT} "
                f"(includes {DEFAULT_TEST_USERNAME} and {DEFAULT_GM_USERNAME})"
            )
            self.stdout.write(
                f"  🎲 Campaigns: {campaigns_count + DEFAULT_CAMPAIGNS_COUNT} "
                f"(includes {DEFAULT_CAMPAIGN_NAME})"
            )
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
            test_characters = self.create_test_characters(
                characters_count, test_campaigns, test_users, verbosity
            )

            self.stdout.write(self.style.SUCCESS("✅ Test data created successfully!"))
            self.stdout.write(f"  👥 Created {len(test_users)} users")
            self.stdout.write(f"  🎲 Created {len(test_campaigns)} campaigns")
            self.stdout.write(f"  🎭 Created {len(test_characters)} characters")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to create test data: {e}"))
            sys.exit(1)

    def clear_test_data(self):
        """Clear existing test data."""
        # Clear all non-superuser users to start fresh
        User.objects.filter(is_superuser=False).delete()

        # Clear test campaigns when models are implemented
        try:
            from campaigns.models import Campaign

            Campaign.objects.filter(name__startswith=DEFAULT_CAMPAIGN_NAME).delete()
        except (ImportError, AttributeError):
            # Campaign model not implemented yet
            pass

        # Clear test characters when models are implemented
        try:
            from characters.models import Character

            Character.objects.filter(name__startswith="Test Character").delete()
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
                "username": DEFAULT_TEST_USERNAME,
                "email": "testuser@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password": "testpass123",
            },
            {
                "username": DEFAULT_GM_USERNAME,
                "email": "gm@example.com",
                "first_name": "Game",
                "last_name": "Master",
                "password": "gmpass123",
            },
        ]

        for user_data in default_users:
            if not User.objects.filter(username=user_data["username"]).exists():
                user = User.objects.create_user(
                    username=user_data["username"],
                    email=user_data["email"],
                    password=user_data["password"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                )
                users.append(user)
                if verbosity >= 2:
                    self.stdout.write(f"  Created user: {user.username}")

        # Create additional test users
        for i in range(1, count + 1):
            username = f"{ADDITIONAL_USER_PREFIX}{i}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f"testuser{i}@example.com",
                    password=f"testpass{i}123",
                    first_name=f"Test{i}",
                    last_name="User",
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

            # Get the first available user as owner
            owner = User.objects.filter(
                username__in=[DEFAULT_TEST_USERNAME, DEFAULT_GM_USERNAME]
            ).first()
            if not owner:
                owner = User.objects.first()

            if owner:
                # Create default test campaign
                if not Campaign.objects.filter(name=DEFAULT_CAMPAIGN_NAME).exists():
                    campaign = Campaign.objects.create(
                        name=DEFAULT_CAMPAIGN_NAME,
                        description="A test campaign for development",
                        game_system="generic_wod",
                        owner=owner,
                        max_characters_per_player=5,  # Allow more for testing
                    )
                    campaigns.append(campaign)
                    if verbosity >= 2:
                        self.stdout.write(f"  Created campaign: {campaign.name}")

                # Create additional test campaigns
                for i in range(1, count + 1):
                    campaign_name = f"{DEFAULT_CAMPAIGN_NAME} {i}"
                    if not Campaign.objects.filter(name=campaign_name).exists():
                        campaign = Campaign.objects.create(
                            name=campaign_name,
                            description=f"Test campaign #{i} for development",
                            game_system="generic_wod",
                            owner=owner,
                            max_characters_per_player=5,  # Allow more for testing
                        )
                        campaigns.append(campaign)
                        if verbosity >= 2:
                            self.stdout.write(f"  Created campaign: {campaign.name}")

        except (ImportError, AttributeError):
            if verbosity >= 2:
                self.stdout.write("  Campaign model not implemented yet, skipping...")

        return campaigns

    def create_test_characters(self, count, campaigns, users, verbosity):
        """Create test characters."""
        if verbosity >= 2:
            self.stdout.write("Creating test characters...")

        characters = []

        try:
            import random

            from characters.models import Character

            # Only create characters if we have campaigns and users
            if not campaigns or not users:
                if verbosity >= 2:
                    self.stdout.write(
                        "  No campaigns or users available, "
                        "skipping character creation..."
                    )
                return characters

            # Track characters per user per campaign to respect limits
            char_counts = {}

            # Create test characters
            for i in range(1, count + 1):
                character_name = f"{ADDITIONAL_CHARACTER_PREFIX}{i}"
                if not Character.objects.filter(name=character_name).exists():
                    # Randomly assign to campaign and user
                    campaign = random.choice(campaigns)  # nosec B311
                    user = random.choice(users)  # nosec B311

                    # Make sure user is a member of the campaign
                    if not campaign.is_member(user):
                        # Add user as a player to the campaign
                        from campaigns.models import CampaignMembership

                        CampaignMembership.objects.get_or_create(
                            campaign=campaign, user=user, defaults={"role": "PLAYER"}
                        )

                    # Check character limit for this user-campaign combination
                    key = (user.id, campaign.id)
                    if key not in char_counts:
                        # Count existing characters for this user in this campaign
                        existing = Character.objects.filter(
                            campaign=campaign, player_owner=user
                        ).count()
                        char_counts[key] = existing

                    # Skip if user already has max characters in this campaign
                    max_chars = campaign.max_characters_per_player
                    if max_chars > 0 and char_counts[key] >= max_chars:
                        if verbosity >= 2:
                            self.stdout.write(
                                f"  Skipping character for {user.username} in "
                                f"{campaign.name} (has {max_chars} character(s))"
                            )
                        continue

                    character = Character.objects.create(
                        name=character_name,
                        description=f"Test character #{i} for development",
                        campaign=campaign,
                        player_owner=user,
                        game_system=campaign.game_system or "Generic",
                    )
                    characters.append(character)
                    char_counts[key] += 1
                    if verbosity >= 2:
                        self.stdout.write(
                            f"  Created character: {character.name} in {campaign.name}"
                        )

        except (ImportError, AttributeError):
            # Character model not implemented yet
            if verbosity >= 2:
                self.stdout.write("  Character model not implemented yet, skipping...")

        return characters
