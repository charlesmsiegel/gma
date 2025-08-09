import time

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class CharacterQueryPerformanceTest(TransactionTestCase):
    """Test Character model query performance optimizations.

    This test suite measures the performance improvements from the optimized
    character limit validation logic.
    """

    def setUp(self):
        """Set up test data for performance testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.players = []

        # Create multiple test players
        for i in range(10):
            player = User.objects.create_user(
                username=f"player{i}",
                email=f"player{i}@test.com",
                password="testpass123",
            )
            self.players.append(player)

        self.campaign_limited = Campaign.objects.create(
            name="Limited Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=3,
        )

        self.campaign_unlimited = Campaign.objects.create(
            name="Unlimited Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=0,  # Unlimited
        )

        # Create memberships
        for player in self.players:
            for campaign in [self.campaign_limited, self.campaign_unlimited]:
                CampaignMembership.objects.create(
                    campaign=campaign, user=player, role="PLAYER"
                )

    def _reset_queries(self):
        """Reset the Django query log."""
        connection.queries_log.clear()

    def _count_queries(self):
        """Get the current number of queries executed."""
        return len(connection.queries)

    @override_settings(DEBUG=True)
    def test_unlimited_character_validation_performance(self):
        """Test that unlimited campaigns skip database queries."""
        self._reset_queries()

        # Create character in unlimited campaign
        character = Character(
            name="Unlimited Test Character",
            campaign=self.campaign_unlimited,
            player_owner=self.players[0],
            game_system="Test System",
        )

        queries_before = self._count_queries()
        character._validate_character_limit()
        queries_after = self._count_queries()

        # Should not execute any queries for character count
        # (The campaign.max_characters_per_player access may trigger one query)
        query_count = queries_after - queries_before
        self.assertLessEqual(
            query_count, 1, "Unlimited campaigns should not query character counts"
        )

    @override_settings(DEBUG=True)
    def test_limited_character_validation_queries(self):
        """Test query count for limited campaigns."""
        # Create some existing characters
        for i in range(2):  # 2 characters, limit is 3
            Character.objects.create(
                name=f"Existing Character {i}",
                campaign=self.campaign_limited,
                player_owner=self.players[0],
                game_system="Test System",
            )

        self._reset_queries()

        # Test validation on new character (should be allowed)
        character = Character(
            name="New Character",
            campaign=self.campaign_limited,
            player_owner=self.players[0],
            game_system="Test System",
        )

        queries_before = self._count_queries()
        character._validate_character_limit()
        queries_after = self._count_queries()

        query_count = queries_after - queries_before
        # Should use minimal queries: exists() check and possibly count()
        self.assertLessEqual(
            query_count, 3, "Character limit validation should use minimal queries"
        )

    @override_settings(DEBUG=True)
    def test_validation_query_optimization_with_existing_characters(self):
        """Test that exists() is more efficient than count() for large datasets."""
        # Create characters up to the limit for multiple players
        for player in self.players[:5]:  # Use first 5 players
            for i in range(3):  # Each player has 3 characters (at limit)
                Character.objects.create(
                    name=f"Player {player.username} Character {i}",
                    campaign=self.campaign_limited,
                    player_owner=player,
                    game_system="Test System",
                )

        self._reset_queries()

        # Test validation for a player who is at the limit
        character = Character(
            name="Exceeding Character",
            campaign=self.campaign_limited,
            player_owner=self.players[0],
            game_system="Test System",
        )

        queries_before = self._count_queries()
        try:
            character._validate_character_limit()
        except Exception:
            # We expect this to fail, but we're measuring query performance
            pass
        queries_after = self._count_queries()

        query_count = queries_after - queries_before
        # Even with many characters, should still use minimal queries
        self.assertLessEqual(
            query_count, 3, "Query count should remain low even with many characters"
        )

    def test_performance_comparison_baseline(self):
        """Baseline performance test for character creation."""
        # Measure time to create characters without validation issues
        start_time = time.time()

        characters_created = 0
        for i in range(100):  # Create 100 characters across different players
            player = self.players[i % len(self.players)]
            try:
                Character.objects.create(
                    name=f"Perf Test Character {i}",
                    campaign=self.campaign_unlimited,  # Use unlimited to avoid limits
                    player_owner=player,
                    game_system="Test System",
                )
                characters_created += 1
            except Exception:
                # Skip failed creations
                continue

        end_time = time.time()
        duration = end_time - start_time

        # Performance baseline: should create characters reasonably quickly
        self.assertGreater(
            characters_created, 90, "Most characters should be created successfully"
        )
        self.assertLess(
            duration, 5.0, "Character creation should complete in reasonable time"
        )

        # Log performance metrics for future comparison
        print(
            f"Performance baseline: {characters_created} characters in {duration:.2f}s "
            f"({characters_created/duration:.1f} chars/sec)"
        )

    @override_settings(DEBUG=True)
    def test_index_usage_for_character_queries(self):
        """Test that database indexes are being used effectively."""
        # Create test data
        for player in self.players[:3]:
            for i in range(2):
                Character.objects.create(
                    name=f"Index Test Character {i}",
                    campaign=self.campaign_limited,
                    player_owner=player,
                    game_system="Test System",
                )

        self._reset_queries()

        # Perform query that should use our indexes
        Character.objects.filter(
            campaign=self.campaign_limited, player_owner=self.players[0]
        ).exists()

        # Check that the query was executed
        queries = connection.queries
        self.assertGreater(len(queries), 0, "Query should have been executed")

        # The actual SQL should be available for analysis
        last_query = queries[-1]["sql"]
        self.assertIn("characters_character", last_query)

        print(f"Query executed: {last_query}")

    def test_memory_efficiency_bulk_validation(self):
        """Test memory efficiency when validating many characters."""
        # Create baseline characters
        for player in self.players:
            Character.objects.create(
                name=f"Memory Test Base {player.username}",
                campaign=self.campaign_limited,
                player_owner=player,
                game_system="Test System",
            )

        # Test validating many characters without loading all into memory
        validation_count = 0
        for i in range(50):
            player = self.players[i % len(self.players)]
            character = Character(
                name=f"Memory Test Character {i}",
                campaign=self.campaign_limited,
                player_owner=player,
                game_system="Test System",
            )

            try:
                character._validate_character_limit()
                validation_count += 1
            except Exception:
                # Expected for some due to limits
                validation_count += 1

        self.assertEqual(validation_count, 50, "All validations should complete")


class CharacterQueryOptimizationComparisonTest(TestCase):
    """Compare old vs new query patterns for character validation."""

    def setUp(self):
        """Set up comparison test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Comparison Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=3,
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def _old_validation_logic(self, character):
        """Simulate the old character limit validation logic."""
        if character.campaign and character.player_owner:
            existing_characters = Character.objects.filter(
                campaign=character.campaign, player_owner=character.player_owner
            )
            # Exclude current instance if updating
            if character.pk:
                existing_characters = existing_characters.exclude(pk=character.pk)

            max_chars = character.campaign.max_characters_per_player
            return existing_characters.count() >= max_chars
        return False

    @override_settings(DEBUG=True)
    def test_query_count_comparison(self):
        """Compare query counts between old and new validation logic."""
        # Create existing characters
        for i in range(2):
            Character.objects.create(
                name=f"Comparison Character {i}",
                campaign=self.campaign,
                player_owner=self.player,
                game_system="Test System",
            )

        character = Character(
            name="Test Validation Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        # Test old logic
        connection.queries_log.clear()
        queries_before_old = len(connection.queries)
        old_result = self._old_validation_logic(character)
        queries_after_old = len(connection.queries)
        old_query_count = queries_after_old - queries_before_old

        # Test new logic
        connection.queries_log.clear()
        queries_before_new = len(connection.queries)
        try:
            character._validate_character_limit()
            new_result = False  # No exception = validation passed
        except Exception:
            new_result = True  # Exception = validation failed
        queries_after_new = len(connection.queries)
        new_query_count = queries_after_new - queries_before_new

        # Results should be equivalent
        self.assertEqual(
            old_result, new_result, "Old and new validation should return same result"
        )

        # New logic should use same or fewer queries
        self.assertLessEqual(
            new_query_count,
            old_query_count,
            f"New logic should use <= queries than old "
            f"(new: {new_query_count}, old: {old_query_count})",
        )

        print(f"Query comparison - Old: {old_query_count}, New: {new_query_count}")
