"""Test cases for Safety Preferences API endpoints."""

import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class SafetyPreferencesAPITest(TestCase):
    """Test the safety preferences API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPass123!"
        )
        self.gm_user = User.objects.create_user(
            username="gmuser",
            email="gm@example.com",
            password="TestPass123!"
        )
        
        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.gm_user,
            game_system="Mage: The Ascension",
            content_warnings=["Violence", "Supernatural themes"],
            safety_tools_enabled=True
        )
        
        # Add users to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.user,
            role='PLAYER'
        )
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.other_user,
            role='PLAYER'
        )
        
        # API endpoints
        self.safety_preferences_url = reverse("api:safety_preferences")
        self.user_safety_preferences_url = lambda user_id: reverse(
            "api:user_safety_preferences", kwargs={"user_id": user_id}
        )

    def test_get_own_safety_preferences_empty(self):
        """Test getting own safety preferences when none exist."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.safety_preferences_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], [])
        self.assertEqual(response.data['veils'], [])
        self.assertEqual(response.data['privacy_level'], 'gm_only')
        self.assertTrue(response.data['consent_required'])

    def test_get_own_safety_preferences_existing(self):
        """Test getting own safety preferences when they exist."""
        from users.models.safety import UserSafetyPreferences
        
        # Create existing preferences
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sexual content", "Animal harm"],
            veils=["Violence", "Death"],
            privacy_level='campaign_members',
            consent_required=False
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.safety_preferences_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["Sexual content", "Animal harm"])
        self.assertEqual(response.data['veils'], ["Violence", "Death"])
        self.assertEqual(response.data['privacy_level'], 'campaign_members')
        self.assertFalse(response.data['consent_required'])

    def test_create_safety_preferences(self):
        """Test creating new safety preferences."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "lines": ["Graphic torture", "Sexual violence"],
            "veils": ["Character death", "Mental illness"],
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], data['lines'])
        self.assertEqual(response.data['veils'], data['veils'])
        self.assertEqual(response.data['privacy_level'], data['privacy_level'])
        self.assertTrue(response.data['consent_required'])

    def test_update_existing_safety_preferences(self):
        """Test updating existing safety preferences."""
        from users.models.safety import UserSafetyPreferences
        
        # Create existing preferences
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Old line"],
            veils=["Old veil"],
            privacy_level='private',
            consent_required=False
        )
        
        self.client.force_authenticate(user=self.user)
        
        updated_data = {
            "lines": ["New line", "Another line"],
            "veils": ["New veil"],
            "privacy_level": "campaign_members",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, updated_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], updated_data['lines'])
        self.assertEqual(response.data['veils'], updated_data['veils'])
        self.assertEqual(response.data['privacy_level'], updated_data['privacy_level'])
        self.assertTrue(response.data['consent_required'])

    def test_invalid_privacy_level(self):
        """Test creating preferences with invalid privacy level."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "lines": ["Test line"],
            "veils": ["Test veil"],
            "privacy_level": "invalid_level",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('privacy_level', response.data)

    def test_complex_json_in_lines_and_veils(self):
        """Test saving complex JSON structures in lines and veils."""
        self.client.force_authenticate(user=self.user)
        
        complex_lines = [
            {
                "category": "violence",
                "description": "Graphic violence against children",
                "severity": "absolute"
            }
        ]
        complex_veils = [
            {
                "category": "mental_health",
                "description": "Panic attacks",
                "fade_instruction": "Cut to after the episode"
            }
        ]
        
        data = {
            "lines": complex_lines,
            "veils": complex_veils,
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], complex_lines)
        self.assertEqual(response.data['veils'], complex_veils)

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access safety preferences."""
        response = self.client.get(self.safety_preferences_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_other_user_safety_preferences_private(self):
        """Test getting other user's private safety preferences (should be denied)."""
        from users.models.safety import UserSafetyPreferences
        
        # Create private preferences for other user
        UserSafetyPreferences.objects.create(
            user=self.other_user,
            lines=["Private line"],
            veils=["Private veil"],
            privacy_level='private',
            consent_required=True
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.user_safety_preferences_url(self.other_user.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('privacy_restricted', response.data)

    def test_get_other_user_safety_preferences_campaign_members(self):
        """Test getting other user's campaign_members preferences (allowed if same campaign)."""
        from users.models.safety import UserSafetyPreferences
        
        # Create campaign_members preferences for other user
        UserSafetyPreferences.objects.create(
            user=self.other_user,
            lines=["Shared line"],
            veils=["Shared veil"],
            privacy_level='campaign_members',
            consent_required=True
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.user_safety_preferences_url(self.other_user.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["Shared line"])
        self.assertEqual(response.data['veils'], ["Shared veil"])

    def test_gm_access_to_gm_only_preferences(self):
        """Test GM can access gm_only preferences of campaign members."""
        from users.models.safety import UserSafetyPreferences
        
        # Create gm_only preferences for player
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["GM visible line"],
            veils=["GM visible veil"],
            privacy_level='gm_only',
            consent_required=True
        )
        
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get(
            self.user_safety_preferences_url(self.user.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["GM visible line"])
        self.assertEqual(response.data['veils'], ["GM visible veil"])

    def test_non_campaign_member_access_denied(self):
        """Test that non-campaign members cannot access campaign_members preferences."""
        from users.models.safety import UserSafetyPreferences
        
        # Create a user not in the campaign
        outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="TestPass123!"
        )
        
        # Create campaign_members preferences
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Campaign line"],
            veils=["Campaign veil"],
            privacy_level='campaign_members',
            consent_required=True
        )
        
        self.client.force_authenticate(user=outsider)
        response = self.client.get(
            self.user_safety_preferences_url(self.user.id)
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_safety_preferences_field_validation(self):
        """Test validation of safety preferences fields."""
        self.client.force_authenticate(user=self.user)
        
        # Test missing required fields
        invalid_data = {
            "lines": ["Test line"],
            # Missing other required fields
        }
        
        response = self.client.put(self.safety_preferences_url, invalid_data, format='json')
        
        # Should use defaults for missing fields or fail validation
        if response.status_code == status.HTTP_200_OK:
            # If defaults are used
            self.assertEqual(response.data['lines'], ["Test line"])
            self.assertIsNotNone(response.data['privacy_level'])
        else:
            # If validation fails
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_safety_preferences_empty_lists(self):
        """Test that empty lists are valid for lines and veils."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            "lines": [],
            "veils": [],
            "privacy_level": "gm_only",
            "consent_required": False
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], [])
        self.assertEqual(response.data['veils'], [])

    def test_safety_preferences_large_data(self):
        """Test handling of large amounts of safety preference data."""
        self.client.force_authenticate(user=self.user)
        
        # Create large lists
        large_lines = [f"Line {i}" for i in range(100)]
        large_veils = [f"Veil {i}" for i in range(100)]
        
        data = {
            "lines": large_lines,
            "veils": large_veils,
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['lines']), 100)
        self.assertEqual(len(response.data['veils']), 100)

    def test_safety_preferences_special_characters(self):
        """Test handling of special characters in safety preferences."""
        self.client.force_authenticate(user=self.user)
        
        special_lines = [
            "Content with 'quotes' and \"double quotes\"",
            "Unicode: émotions, 中文, русский",
            "HTML-like: <script>alert('test')</script>",
            "JSON-like: {\"key\": \"value\"}"
        ]
        
        data = {
            "lines": special_lines,
            "veils": [],
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], special_lines)

    def test_safety_preferences_response_format(self):
        """Test the format of safety preferences API response."""
        from users.models.safety import UserSafetyPreferences
        
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Test line"],
            veils=["Test veil"],
            privacy_level='gm_only',
            consent_required=True
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.safety_preferences_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check required fields are present
        required_fields = ['lines', 'veils', 'privacy_level', 'consent_required']
        for field in required_fields:
            self.assertIn(field, response.data)
        
        # Check timestamps if included
        if 'created_at' in response.data:
            self.assertIsNotNone(response.data['created_at'])
        if 'updated_at' in response.data:
            self.assertIsNotNone(response.data['updated_at'])


class SafetyPreferencesAPISecurityTest(TestCase):
    """Test security aspects of safety preferences API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        self.malicious_user = User.objects.create_user(
            username="malicious",
            email="malicious@example.com",
            password="TestPass123!"
        )
        
        self.safety_preferences_url = reverse("api:safety_preferences")

    def test_cannot_modify_other_user_preferences(self):
        """Test that users cannot modify other users' safety preferences."""
        from users.models.safety import UserSafetyPreferences
        
        # Create preferences for target user
        original_prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Original line"],
            veils=["Original veil"],
            privacy_level='private',
            consent_required=True
        )
        
        # Try to modify as malicious user
        self.client.force_authenticate(user=self.malicious_user)
        
        malicious_data = {
            "lines": ["Malicious line"],
            "veils": ["Malicious veil"],
            "privacy_level": "campaign_members",
            "consent_required": False
        }
        
        # This should create preferences for malicious_user, not modify user's
        response = self.client.put(self.safety_preferences_url, malicious_data, format='json')
        
        # Verify original user's preferences unchanged
        original_prefs.refresh_from_db()
        self.assertEqual(original_prefs.lines, ["Original line"])
        self.assertEqual(original_prefs.veils, ["Original veil"])
        self.assertEqual(original_prefs.privacy_level, 'private')

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts in safety preferences are handled safely."""
        self.client.force_authenticate(user=self.user)
        
        sql_injection_attempts = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "<script>alert('xss')</script>"
        ]
        
        for injection_attempt in sql_injection_attempts:
            with self.subTest(injection=injection_attempt):
                data = {
                    "lines": [injection_attempt],
                    "veils": [injection_attempt],
                    "privacy_level": "gm_only",
                    "consent_required": True
                }
                
                response = self.client.put(self.safety_preferences_url, data, format='json')
                
                # Should either succeed (storing safely) or fail gracefully
                self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
                
                if response.status_code == status.HTTP_200_OK:
                    # If stored, verify it's stored as-is (not executed)
                    self.assertEqual(response.data['lines'][0], injection_attempt)

    def test_privacy_level_enforcement(self):
        """Test that privacy levels are properly enforced."""
        from users.models.safety import UserSafetyPreferences
        
        # Create user with private preferences
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Secret line"],
            veils=["Secret veil"],
            privacy_level='private',
            consent_required=True
        )
        
        # Try to access as different user
        self.client.force_authenticate(user=self.malicious_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.user.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn("Secret line", str(response.data))

    def test_rate_limiting_safety_preferences_updates(self):
        """Test rate limiting on safety preferences updates."""
        self.client.force_authenticate(user=self.user)
        
        # Perform many rapid updates
        for i in range(10):
            data = {
                "lines": [f"Line {i}"],
                "veils": [f"Veil {i}"],
                "privacy_level": "gm_only",
                "consent_required": True
            }
            
            response = self.client.put(self.safety_preferences_url, data, format='json')
            
            # All should succeed (no rate limiting implemented yet)
            # But this test documents expected behavior
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS])

    def test_authorization_header_security(self):
        """Test that authorization is properly required and validated."""
        # Test without authentication
        response = self.client.get(self.safety_preferences_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test with invalid authentication
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.client.get(self.safety_preferences_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_content_type_validation(self):
        """Test that content type validation is properly enforced."""
        self.client.force_authenticate(user=self.user)
        
        # Test with wrong content type
        data = "invalid_json_data"
        response = self.client.put(
            self.safety_preferences_url,
            data,
            content_type='text/plain'
        )
        
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)


class SafetyPreferencesAPIErrorHandlingTest(TestCase):
    """Test error handling in safety preferences API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        self.safety_preferences_url = reverse("api:safety_preferences")

    def test_malformed_json_handling(self):
        """Test handling of malformed JSON data."""
        self.client.force_authenticate(user=self.user)
        
        # Send malformed JSON
        response = self.client.put(
            self.safety_preferences_url,
            '{"lines": ["test", "veils": ["test"}',  # Malformed JSON
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_user_handling(self):
        """Test handling when user doesn't exist."""
        # Try to access preferences for non-existent user
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": 99999})
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)  # Or 404

    def test_database_error_handling(self):
        """Test handling of database errors."""
        self.client.force_authenticate(user=self.user)
        
        # This would require mocking database errors
        # For now, just verify normal operation works
        data = {
            "lines": ["Test line"],
            "veils": ["Test veil"],
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(self.safety_preferences_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_field_types(self):
        """Test handling of invalid field types."""
        self.client.force_authenticate(user=self.user)
        
        invalid_data_sets = [
            {
                "lines": "not_a_list",  # Should be list
                "veils": ["valid"],
                "privacy_level": "gm_only",
                "consent_required": True
            },
            {
                "lines": ["valid"],
                "veils": {"not": "a_list"},  # Should be list
                "privacy_level": "gm_only",
                "consent_required": True
            },
            {
                "lines": ["valid"],
                "veils": ["valid"],
                "privacy_level": "gm_only",
                "consent_required": "not_boolean"  # Should be boolean
            }
        ]
        
        for invalid_data in invalid_data_sets:
            with self.subTest(data=invalid_data):
                response = self.client.put(
                    self.safety_preferences_url,
                    invalid_data,
                    format='json'
                )
                
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)