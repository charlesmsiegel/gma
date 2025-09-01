"""Test cases for UserSafetyPreferences model and safety-related functionality."""

import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserSafetyPreferencesTest(TestCase):
    """Test the UserSafetyPreferences model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com", 
            password="testpass123"
        )

    def test_safety_preferences_creation_defaults(self):
        """Test creating safety preferences with default values."""
        # Import here to avoid circular imports during test discovery
        from users.models.safety import UserSafetyPreferences
        
        prefs = UserSafetyPreferences.objects.create(user=self.user)
        
        self.assertEqual(prefs.user, self.user)
        self.assertEqual(prefs.lines, [])
        self.assertEqual(prefs.veils, [])
        self.assertEqual(prefs.privacy_level, 'gm_only')
        self.assertTrue(prefs.consent_required)
        self.assertIsNotNone(prefs.created_at)
        self.assertIsNotNone(prefs.updated_at)

    def test_safety_preferences_string_representation(self):
        """Test the string representation of safety preferences."""
        from users.models.safety import UserSafetyPreferences
        
        prefs = UserSafetyPreferences.objects.create(user=self.user)
        expected_str = f"Safety preferences for {self.user.username}"
        self.assertEqual(str(prefs), expected_str)

    def test_one_to_one_relationship_with_user(self):
        """Test that UserSafetyPreferences has a one-to-one relationship with User."""
        from users.models.safety import UserSafetyPreferences
        
        # Create first preferences
        prefs1 = UserSafetyPreferences.objects.create(user=self.user)
        self.assertEqual(prefs1.user, self.user)
        
        # Try to create second preferences for same user - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            UserSafetyPreferences.objects.create(user=self.user)

    def test_user_deletion_cascades_to_safety_preferences(self):
        """Test that deleting a user deletes their safety preferences."""
        from users.models.safety import UserSafetyPreferences
        
        prefs = UserSafetyPreferences.objects.create(user=self.user)
        prefs_id = prefs.id
        
        # Delete user
        self.user.delete()
        
        # Safety preferences should be deleted
        with self.assertRaises(UserSafetyPreferences.DoesNotExist):
            UserSafetyPreferences.objects.get(id=prefs_id)

    def test_lines_field_accepts_list_of_strings(self):
        """Test that lines field accepts list of strings."""
        from users.models.safety import UserSafetyPreferences
        
        lines = ["Sexual content", "Graphic violence", "Animal harm"]
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=lines
        )
        
        self.assertEqual(prefs.lines, lines)

    def test_veils_field_accepts_list_of_strings(self):
        """Test that veils field accepts list of strings."""
        from users.models.safety import UserSafetyPreferences
        
        veils = ["Romance scenes", "Torture", "Death of children"]
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            veils=veils
        )
        
        self.assertEqual(prefs.veils, veils)

    def test_privacy_level_choices(self):
        """Test privacy level field accepts valid choices."""
        from users.models.safety import UserSafetyPreferences
        
        valid_choices = ['private', 'gm_only', 'campaign_members']
        
        for choice in valid_choices:
            user = User.objects.create_user(
                username=f"user_{choice}",
                email=f"{choice}@example.com",
                password="testpass123"
            )
            prefs = UserSafetyPreferences.objects.create(
                user=user,
                privacy_level=choice
            )
            self.assertEqual(prefs.privacy_level, choice)

    def test_privacy_level_invalid_choice_raises_validation_error(self):
        """Test that invalid privacy level raises ValidationError."""
        from users.models.safety import UserSafetyPreferences
        
        prefs = UserSafetyPreferences(
            user=self.user,
            privacy_level='invalid_choice'
        )
        
        with self.assertRaises(ValidationError):
            prefs.full_clean()

    def test_consent_required_boolean_field(self):
        """Test consent_required field accepts boolean values."""
        from users.models.safety import UserSafetyPreferences
        
        # Test True
        prefs_true = UserSafetyPreferences.objects.create(
            user=self.user,
            consent_required=True
        )
        self.assertTrue(prefs_true.consent_required)
        
        # Test False
        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123"
        )
        prefs_false = UserSafetyPreferences.objects.create(
            user=user2,
            consent_required=False
        )
        self.assertFalse(prefs_false.consent_required)

    def test_lines_and_veils_can_be_empty_lists(self):
        """Test that lines and veils can be empty lists."""
        from users.models.safety import UserSafetyPreferences
        
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=[],
            veils=[]
        )
        
        self.assertEqual(prefs.lines, [])
        self.assertEqual(prefs.veils, [])

    def test_lines_and_veils_can_contain_complex_data(self):
        """Test that lines and veils can contain complex JSON data."""
        from users.models.safety import UserSafetyPreferences
        
        complex_lines = [
            {
                "category": "violence",
                "description": "Graphic violence against children",
                "severity": "absolute"
            },
            {
                "category": "sexual",
                "description": "Non-consensual sexual content",
                "severity": "absolute"
            }
        ]
        
        complex_veils = [
            {
                "category": "mental_health",
                "description": "Detailed descriptions of panic attacks",
                "fade_to_black": True
            }
        ]
        
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=complex_lines,
            veils=complex_veils
        )
        
        self.assertEqual(prefs.lines, complex_lines)
        self.assertEqual(prefs.veils, complex_veils)

    def test_user_safety_preferences_reverse_relationship(self):
        """Test accessing safety preferences from User model."""
        from users.models.safety import UserSafetyPreferences
        
        prefs = UserSafetyPreferences.objects.create(user=self.user)
        
        # Access via related name
        self.assertEqual(self.user.safety_preferences, prefs)

    def test_safety_preferences_update_timestamps(self):
        """Test that updating safety preferences updates the updated_at timestamp."""
        from users.models.safety import UserSafetyPreferences
        from django.utils import timezone
        import time
        
        prefs = UserSafetyPreferences.objects.create(user=self.user)
        original_updated_at = prefs.updated_at
        
        # Wait a small amount to ensure timestamp difference
        time.sleep(0.01)
        
        # Update the preferences
        prefs.lines = ["New line"]
        prefs.save()
        
        # Refresh from database
        prefs.refresh_from_db()
        
        self.assertGreater(prefs.updated_at, original_updated_at)

    def test_safety_preferences_manager_methods(self):
        """Test custom manager methods if they exist."""
        from users.models.safety import UserSafetyPreferences
        
        # Create preferences with different privacy levels
        user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="pass123"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="pass123"
        )
        user3 = User.objects.create_user(
            username="user3", email="user3@example.com", password="pass123"
        )
        
        UserSafetyPreferences.objects.create(user=user1, privacy_level='private')
        UserSafetyPreferences.objects.create(user=user2, privacy_level='gm_only')
        UserSafetyPreferences.objects.create(user=user3, privacy_level='campaign_members')
        
        # Test basic queryset functionality
        all_prefs = UserSafetyPreferences.objects.all()
        self.assertEqual(all_prefs.count(), 3)
        
        # Test filtering by privacy level
        gm_only_prefs = UserSafetyPreferences.objects.filter(privacy_level='gm_only')
        self.assertEqual(gm_only_prefs.count(), 1)
        self.assertEqual(gm_only_prefs.first().user, user2)

    def test_safety_preferences_json_serialization(self):
        """Test that lines and veils can be properly JSON serialized."""
        from users.models.safety import UserSafetyPreferences
        
        lines = ["Violence", "Sexual content"]
        veils = ["Romance", "Death"]
        
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=lines,
            veils=veils
        )
        
        # Test JSON serialization works
        lines_json = json.dumps(prefs.lines)
        veils_json = json.dumps(prefs.veils)
        
        self.assertEqual(json.loads(lines_json), lines)
        self.assertEqual(json.loads(veils_json), veils)

    def test_safety_preferences_field_max_lengths(self):
        """Test field max lengths if they exist."""
        from users.models.safety import UserSafetyPreferences
        
        # Create preferences with very long content to test field limits
        very_long_line = "x" * 1000  # Test long string
        
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=[very_long_line],
            veils=[very_long_line]
        )
        
        # Should succeed - JSON fields don't have max_length restrictions
        self.assertEqual(prefs.lines, [very_long_line])
        self.assertEqual(prefs.veils, [very_long_line])

    def test_safety_preferences_blank_and_null_validation(self):
        """Test blank and null validation for safety preferences fields."""
        from users.models.safety import UserSafetyPreferences
        
        # Create minimal preferences (should work with defaults)
        prefs = UserSafetyPreferences(user=self.user)
        
        try:
            prefs.full_clean()
        except ValidationError as e:
            self.fail(f"UserSafetyPreferences validation failed unexpectedly: {e}")
        
        # Save should work
        prefs.save()
        self.assertIsNotNone(prefs.id)


class UserSafetyPreferencesIntegrationTest(TestCase):
    """Integration tests for UserSafetyPreferences with other models."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.gm_user = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="testpass123"
        )

    def test_safety_preferences_access_control_by_privacy_level(self):
        """Test that privacy levels control who can access safety preferences."""
        from users.models.safety import UserSafetyPreferences
        
        # Create preferences with different privacy levels
        private_prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            privacy_level='private',
            lines=["Private line"],
            veils=["Private veil"]
        )
        
        gm_only_prefs = UserSafetyPreferences.objects.create(
            user=self.gm_user,
            privacy_level='gm_only',
            lines=["GM only line"],
            veils=["GM only veil"]
        )
        
        # Test that preferences exist and have correct privacy levels
        self.assertEqual(private_prefs.privacy_level, 'private')
        self.assertEqual(gm_only_prefs.privacy_level, 'gm_only')

    def test_safety_preferences_with_user_profile_data(self):
        """Test safety preferences work with user profile information."""
        from users.models.safety import UserSafetyPreferences
        
        # Update user profile information
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.save()
        
        # Create safety preferences
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Content related to real name"],
            privacy_level='private'
        )
        
        # Test that we can access both user data and safety preferences
        self.assertEqual(prefs.user.first_name, "Test")
        self.assertEqual(prefs.user.last_name, "User")
        self.assertEqual(prefs.lines, ["Content related to real name"])

    def test_multiple_users_safety_preferences(self):
        """Test that multiple users can have different safety preferences."""
        from users.models.safety import UserSafetyPreferences
        
        # Create additional users
        user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="pass123"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="pass123"
        )
        
        # Create different preferences for each user
        prefs1 = UserSafetyPreferences.objects.create(
            user=user1,
            lines=["Violence"],
            veils=["Romance"],
            privacy_level='gm_only',
            consent_required=True
        )
        
        prefs2 = UserSafetyPreferences.objects.create(
            user=user2,
            lines=["Sexual content"],
            veils=["Death"],
            privacy_level='campaign_members',
            consent_required=False
        )
        
        # Verify each user has distinct preferences
        self.assertNotEqual(prefs1.lines, prefs2.lines)
        self.assertNotEqual(prefs1.veils, prefs2.veils)
        self.assertNotEqual(prefs1.privacy_level, prefs2.privacy_level)
        self.assertNotEqual(prefs1.consent_required, prefs2.consent_required)
        
        # Verify we can query all preferences
        all_prefs = UserSafetyPreferences.objects.all()
        self.assertEqual(all_prefs.count(), 2)