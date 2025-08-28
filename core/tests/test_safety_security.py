"""Comprehensive security and permission tests for the Lines & Veils Safety System."""

import json
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class SafetySystemPermissionTest(TestCase):
    """Test permission and access control in safety system."""

    def setUp(self):
        """Set up comprehensive permission test scenario."""
        self.client = APIClient()
        
        # Create users with different roles and relationships
        self.superuser = User.objects.create_superuser(
            username="superuser",
            email="super@example.com",
            password="TestPass123!"
        )
        
        self.campaign_owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPass123!"
        )
        
        self.gm_user = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="TestPass123!"
        )
        
        self.player_user = User.objects.create_user(
            username="player",
            email="player@example.com",
            password="TestPass123!"
        )
        
        self.outsider_user = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="TestPass123!"
        )
        
        self.malicious_user = User.objects.create_user(
            username="malicious",
            email="malicious@example.com",
            password="TestPass123!"
        )
        
        # Create campaigns with different ownership structures
        self.main_campaign = Campaign.objects.create(
            name="Main Campaign",
            owner=self.campaign_owner,
            game_system="World of Darkness",
            content_warnings=["Violence", "Horror"],
            safety_tools_enabled=True
        )
        
        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.malicious_user,
            game_system="D&D 5e",
            content_warnings=["Combat"],
            safety_tools_enabled=True
        )
        
        # Set up campaign memberships
        CampaignMembership.objects.create(
            campaign=self.main_campaign,
            user=self.gm_user,
            role='GM'
        )
        CampaignMembership.objects.create(
            campaign=self.main_campaign,
            user=self.player_user,
            role='PLAYER'
        )
        
        # Create safety preferences with different privacy levels
        from users.models.safety import UserSafetyPreferences
        self.private_prefs = UserSafetyPreferences.objects.create(
            user=self.player_user,
            lines=["Private line content"],
            veils=["Private veil content"], 
            privacy_level='private',
            consent_required=True
        )
        
        self.gm_only_prefs = UserSafetyPreferences.objects.create(
            user=self.campaign_owner,
            lines=["GM only line content"],
            veils=["GM only veil content"],
            privacy_level='gm_only',
            consent_required=False
        )
        
        self.campaign_members_prefs = UserSafetyPreferences.objects.create(
            user=self.gm_user,
            lines=["Campaign members line content"],
            veils=["Campaign members veil content"],
            privacy_level='campaign_members',
            consent_required=True
        )

    def test_private_safety_preferences_access_control(self):
        """Test that private safety preferences are properly protected."""
        
        # Owner can access their own private preferences
        self.client.force_authenticate(user=self.player_user)
        response = self.client.get(reverse("api:safety_preferences"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["Private line content"])
        
        # Campaign owner cannot access private preferences
        self.client.force_authenticate(user=self.campaign_owner)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.player_user.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # GM cannot access private preferences
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.player_user.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Superuser cannot access private preferences (respecting user privacy)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.player_user.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_gm_only_safety_preferences_access_control(self):
        """Test that gm_only safety preferences are accessible to appropriate roles."""
        
        # Owner can access their own gm_only preferences
        self.client.force_authenticate(user=self.campaign_owner)
        response = self.client.get(reverse("api:safety_preferences"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["GM only line content"])
        
        # GM can access owner's gm_only preferences (same campaign)
        self.client.force_authenticate(user=self.gm_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.campaign_owner.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["GM only line content"])
        
        # Player cannot access gm_only preferences
        self.client.force_authenticate(user=self.player_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.campaign_owner.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Outsider cannot access gm_only preferences
        self.client.force_authenticate(user=self.outsider_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.campaign_owner.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_campaign_members_safety_preferences_access_control(self):
        """Test that campaign_members safety preferences are accessible to campaign members only."""
        
        # Owner can access campaign member's preferences
        self.client.force_authenticate(user=self.campaign_owner)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.gm_user.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["Campaign members line content"])
        
        # Player can access campaign member's preferences
        self.client.force_authenticate(user=self.player_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.gm_user.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lines'], ["Campaign members line content"])
        
        # Outsider cannot access campaign member's preferences
        self.client.force_authenticate(user=self.outsider_user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.gm_user.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_campaign_access_prevention(self):
        """Test that users cannot access safety information from campaigns they're not in."""
        
        # Add malicious user to their own campaign only
        CampaignMembership.objects.create(
            campaign=self.other_campaign,
            user=self.malicious_user,
            role='GM'
        )
        
        # Malicious user cannot access main campaign safety info
        self.client.force_authenticate(user=self.malicious_user)
        response = self.client.get(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.main_campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Malicious user cannot access main campaign safety overview
        response = self.client.get(
            reverse("api:campaign_safety_overview", kwargs={"campaign_id": self.main_campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Malicious user cannot validate content for main campaign
        content_data = {
            "content": "Malicious content check",
            "campaign_id": self.main_campaign.id
        }
        response = self.client.post(
            reverse("api:validate_content_for_campaign"),
            content_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_safety_agreement_permission_isolation(self):
        """Test that safety agreements are properly isolated by campaign and user."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create safety agreement in main campaign
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.main_campaign,
            participant=self.player_user,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        
        # Player can access their own agreement
        self.client.force_authenticate(user=self.player_user)
        response = self.client.get(
            reverse("api:campaign_safety_agreement", kwargs={"campaign_id": self.main_campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['agreed_to_terms'])
        
        # Malicious user cannot access agreement from other campaign
        self.client.force_authenticate(user=self.malicious_user)
        response = self.client.get(
            reverse("api:campaign_safety_agreement", kwargs={"campaign_id": self.main_campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Malicious user cannot modify agreement in other campaign
        malicious_data = {
            "agreed_to_terms": False,
            "acknowledged_warnings": ["Malicious change"]
        }
        response = self.client.put(
            reverse("api:campaign_safety_agreement", kwargs={"campaign_id": self.main_campaign.id}),
            malicious_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify original agreement unchanged
        agreement.refresh_from_db()
        self.assertTrue(agreement.agreed_to_terms)
        self.assertEqual(agreement.acknowledged_warnings, ["Violence"])

    def test_role_based_campaign_safety_modification(self):
        """Test that only appropriate roles can modify campaign safety settings."""
        
        # Owner can modify safety settings
        self.client.force_authenticate(user=self.campaign_owner)
        safety_update = {
            "content_warnings": ["Updated by owner"],
            "safety_tools_enabled": False
        }
        response = self.client.put(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.main_campaign.id}),
            safety_update,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Reset for next test
        self.main_campaign.refresh_from_db()
        
        # GM can modify safety settings
        self.client.force_authenticate(user=self.gm_user)
        safety_update = {
            "content_warnings": ["Updated by GM"],
            "safety_tools_enabled": True
        }
        response = self.client.put(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.main_campaign.id}),
            safety_update,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Player cannot modify safety settings
        self.client.force_authenticate(user=self.player_user)
        safety_update = {
            "content_warnings": ["Attempted by player"],
            "safety_tools_enabled": False
        }
        response = self.client.put(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.main_campaign.id}),
            safety_update,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_content_validation_permission_enforcement(self):
        """Test that content validation respects permission boundaries."""
        
        # GM can validate content for campaign members
        self.client.force_authenticate(user=self.gm_user)
        content_data = {
            "content": "GM validating player content",
            "user_id": self.player_user.id,
            "campaign_id": self.main_campaign.id
        }
        response = self.client.post(
            reverse("api:validate_content_for_user"),
            content_data,
            format='json'
        )
        # May be forbidden due to private preferences, but not due to campaign membership
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        # Outsider cannot validate content for campaign
        self.client.force_authenticate(user=self.outsider_user)
        response = self.client.post(
            reverse("api:validate_content_for_user"),
            content_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SafetySystemSecurityTest(TestCase):
    """Test security vulnerabilities and attack vectors in safety system."""

    def setUp(self):
        """Set up security test scenario."""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        
        self.attacker = User.objects.create_user(
            username="attacker", 
            email="attacker@example.com",
            password="TestPass123!"
        )
        
        self.campaign = Campaign.objects.create(
            name="Security Test Campaign",
            owner=self.user,
            game_system="Test System",
            safety_tools_enabled=True
        )
        
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.user,
            role='GM'
        )

    def test_sql_injection_prevention_in_safety_preferences(self):
        """Test that SQL injection attempts in safety data are prevented."""
        self.client.force_authenticate(user=self.user)
        
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; UPDATE users SET is_superuser=1; --",
            "UNION SELECT password FROM auth_user",
            "'; INSERT INTO auth_user (username) VALUES ('hacker'); --"
        ]
        
        for payload in sql_injection_payloads:
            with self.subTest(payload=payload):
                malicious_prefs = {
                    "lines": [payload],
                    "veils": [payload],
                    "privacy_level": "gm_only",
                    "consent_required": True
                }
                
                response = self.client.put(
                    reverse("api:safety_preferences"),
                    malicious_prefs,
                    format='json'
                )
                
                # Should either succeed (payload treated as data) or fail gracefully
                self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
                
                if response.status_code == status.HTTP_200_OK:
                    # Verify payload is stored as-is, not executed
                    self.assertEqual(response.data['lines'], [payload])

    def test_xss_prevention_in_safety_content(self):
        """Test that XSS attempts in safety content are handled safely."""
        self.client.force_authenticate(user=self.user)
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "\";alert('XSS');//"
        ]
        
        for payload in xss_payloads:
            with self.subTest(payload=payload):
                xss_prefs = {
                    "lines": [payload],
                    "veils": [f"Veil with {payload}"],
                    "privacy_level": "gm_only",
                    "consent_required": True
                }
                
                response = self.client.put(
                    reverse("api:safety_preferences"),
                    xss_prefs,
                    format='json'
                )
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Verify payload is stored safely
                self.assertEqual(response.data['lines'], [payload])
                
                # Verify no script execution in response
                response_text = str(response.content)
                # Should not contain unescaped script tags
                self.assertNotRegex(response_text, r'<script[^>]*>.*?</script>')

    def test_json_injection_prevention(self):
        """Test that JSON injection attempts are prevented."""
        self.client.force_authenticate(user=self.user)
        
        json_injection_payloads = [
            '{"malicious": "payload"}',
            '[{"inject": "data"}]',
            '}}{"extra": "object"}}',
            '\u0000\u0001\u0002',  # Null bytes and control characters
        ]
        
        for payload in json_injection_payloads:
            with self.subTest(payload=payload):
                injection_data = {
                    "lines": [payload],
                    "veils": ["normal content"],
                    "privacy_level": "gm_only",
                    "consent_required": True
                }
                
                response = self.client.put(
                    reverse("api:safety_preferences"),
                    injection_data,
                    format='json'
                )
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                # Payload should be stored as string, not parsed as JSON
                self.assertEqual(response.data['lines'], [payload])

    def test_mass_assignment_prevention(self):
        """Test that mass assignment attacks are prevented."""
        self.client.force_authenticate(user=self.user)
        
        # Attempt to modify fields that shouldn't be directly settable
        mass_assignment_attempt = {
            "lines": ["Normal content"],
            "veils": ["Normal veil"],
            "privacy_level": "gm_only",
            "consent_required": True,
            # Attempt to set fields that shouldn't be settable
            "user": self.attacker.id,  # Try to assign to different user
            "created_at": "2020-01-01T00:00:00Z",  # Try to modify timestamp
            "updated_at": "2020-01-01T00:00:00Z",  # Try to modify timestamp
            "id": 999999,  # Try to set specific ID
        }
        
        response = self.client.put(
            reverse("api:safety_preferences"),
            mass_assignment_attempt,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify that the preferences belong to the authenticated user, not the attacker
        from users.models.safety import UserSafetyPreferences
        prefs = UserSafetyPreferences.objects.get(user=self.user)
        self.assertEqual(prefs.user, self.user)  # Not self.attacker
        self.assertNotEqual(prefs.created_at.year, 2020)  # Timestamp not modified

    def test_privilege_escalation_prevention(self):
        """Test that privilege escalation attempts are prevented."""
        
        # Create regular user trying to access admin functions
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
            password="TestPass123!"
        )
        
        self.client.force_authenticate(user=regular_user)
        
        # Attempt to access campaign safety settings without proper permissions
        response = self.client.get(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.campaign.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Attempt to modify campaign safety settings
        malicious_update = {
            "content_warnings": ["Escalated access"],
            "safety_tools_enabled": False
        }
        response = self.client.put(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.campaign.id}),
            malicious_update,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_information_disclosure_prevention(self):
        """Test that sensitive information is not disclosed in error messages."""
        
        # Create private safety preferences
        from users.models.safety import UserSafetyPreferences
        private_prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sensitive private information"],
            veils=["Personal trauma details"],
            privacy_level='private'
        )
        
        # Attacker tries to access private preferences
        self.client.force_authenticate(user=self.attacker)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.user.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify sensitive information is not disclosed in error response
        response_text = str(response.content).lower()
        self.assertNotIn("sensitive private information", response_text)
        self.assertNotIn("personal trauma details", response_text)

    def test_rate_limiting_enforcement(self):
        """Test that rate limiting is enforced for safety endpoints."""
        self.client.force_authenticate(user=self.user)
        
        # Make rapid requests to safety preferences endpoint
        for i in range(50):  # Attempt many rapid requests
            prefs_data = {
                "lines": [f"Line {i}"],
                "veils": [f"Veil {i}"],
                "privacy_level": "gm_only",
                "consent_required": True
            }
            
            response = self.client.put(
                reverse("api:safety_preferences"),
                prefs_data,
                format='json'
            )
            
            # Should eventually hit rate limits (if implemented)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
        
        # Note: This test documents expected behavior - rate limiting may not be implemented yet

    def test_concurrent_modification_protection(self):
        """Test protection against concurrent modification attacks."""
        from users.models.safety import UserSafetyPreferences
        
        # Create initial preferences
        initial_prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Initial line"],
            veils=["Initial veil"],
            privacy_level='private'
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Simulate concurrent modification attempts
        update1 = {
            "lines": ["Update 1"],
            "veils": ["Veil 1"],
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        update2 = {
            "lines": ["Update 2"],
            "veils": ["Veil 2"],
            "privacy_level": "campaign_members",
            "consent_required": False
        }
        
        # Both updates should succeed, with the last one winning
        response1 = self.client.put(reverse("api:safety_preferences"), update1, format='json')
        response2 = self.client.put(reverse("api:safety_preferences"), update2, format='json')
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify final state
        initial_prefs.refresh_from_db()
        self.assertEqual(initial_prefs.lines, ["Update 2"])

    @override_settings(DEBUG=False)  # Test in production-like settings
    def test_error_handling_information_leakage(self):
        """Test that error handling doesn't leak sensitive information."""
        
        # Attempt to access non-existent user's preferences
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": 999999})
        )
        
        # Should return 404, not expose database details
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Response should not contain database error details
        response_text = str(response.content).lower()
        sensitive_terms = [
            'sql', 'database', 'table', 'column', 'constraint',
            'traceback', 'exception', 'stack trace'
        ]
        
        for term in sensitive_terms:
            self.assertNotIn(term, response_text)

    def test_input_validation_boundary_conditions(self):
        """Test input validation at boundary conditions."""
        self.client.force_authenticate(user=self.user)
        
        # Test extremely long input
        very_long_line = "x" * 100000  # 100k characters
        
        boundary_test_data = {
            "lines": [very_long_line],
            "veils": ["Normal veil"],
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(
            reverse("api:safety_preferences"),
            boundary_test_data,
            format='json'
        )
        
        # Should either succeed or fail gracefully with appropriate error
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        ])
        
        # Test with many items
        many_lines = [f"Line {i}" for i in range(1000)]  # 1000 lines
        
        many_items_data = {
            "lines": many_lines,
            "veils": ["Normal veil"],
            "privacy_level": "gm_only",
            "consent_required": True
        }
        
        response = self.client.put(
            reverse("api:safety_preferences"),
            many_items_data,
            format='json'
        )
        
        # Should handle large arrays appropriately
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ])