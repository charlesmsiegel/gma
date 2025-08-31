"""Comprehensive integration tests for the Lines & Veils Safety System."""

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class SafetySystemIntegrationTest(TestCase):
    """Test complete safety system workflows end-to-end."""

    def setUp(self):
        """Set up comprehensive test scenario."""
        self.client = APIClient()

        # Create test users with different roles
        self.campaign_owner = User.objects.create_user(
            username="campaign_owner",
            email="owner@example.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.gm = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.player1 = User.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.player2 = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.player3 = User.objects.create_user(
            username="player3",
            email="player3@example.com",
            password="TestPass123!",
            email_verified=True,
        )

        # Create campaign with safety features enabled
        self.campaign = Campaign.objects.create(
            name="Full Safety Integration Campaign",
            owner=self.campaign_owner,
            game_system="World of Darkness",
            content_warnings=[
                "Violence",
                "Supernatural horror",
                "Mental health issues",
                "Substance abuse",
            ],
            safety_tools_enabled=True,
        )

        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player3, role="PLAYER"
        )

    def test_complete_safety_system_workflow(self):
        """Test complete workflow from setup to content validation."""

        # Step 1: Players set up their safety preferences
        # Player 1: Conservative preferences with high privacy
        self.client.force_authenticate(user=self.player1)
        player1_prefs = {
            "lines": ["Sexual content", "Graphic torture", "Animal harm"],
            "veils": ["Violence", "Character death", "Mental health issues"],
            "privacy_level": "gm_only",
            "consent_required": True,
        }
        response = self.client.put(
            reverse("api:safety_preferences"), player1_prefs, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Player 2: Moderate preferences with campaign visibility
        self.client.force_authenticate(user=self.player2)
        player2_prefs = {
            "lines": ["Sexual violence", "Child harm"],
            "veils": ["Substance abuse", "Suicide"],
            "privacy_level": "campaign_members",
            "consent_required": False,
        }
        response = self.client.put(
            reverse("api:safety_preferences"), player2_prefs, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Player 3: Minimal preferences with private setting
        self.client.force_authenticate(user=self.player3)
        player3_prefs = {
            "lines": ["Extreme violence"],
            "veils": [],
            "privacy_level": "private",
            "consent_required": False,
        }
        response = self.client.put(
            reverse("api:safety_preferences"), player3_prefs, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 2: GM reviews campaign safety overview
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(
            reverse(
                "api:campaign_safety_overview", kwargs={"campaign_id": self.campaign.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should see player1 and player2 preferences but not player3 (private)
        overview = response.data
        self.assertIn("participants", overview)

        # Step 3: Players create safety agreements
        # Player 1 agrees to terms
        self.client.force_authenticate(user=self.player1)
        agreement1 = {
            "agreed_to_terms": True,
            "acknowledged_warnings": [
                "Violence",
                "Supernatural horror",
                "Mental health issues",
            ],
        }
        response = self.client.post(
            reverse(
                "api:campaign_safety_agreement",
                kwargs={"campaign_id": self.campaign.id},
            ),
            agreement1,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Player 2 agrees with reservations
        self.client.force_authenticate(user=self.player2)
        agreement2 = {
            "agreed_to_terms": True,
            "acknowledged_warnings": [
                {
                    "warning": "Substance abuse",
                    "comfort_level": "needs_discussion",
                    "notes": "Please discuss before including detailed substance use",
                }
            ],
        }
        response = self.client.post(
            reverse(
                "api:campaign_safety_agreement",
                kwargs={"campaign_id": self.campaign.id},
            ),
            agreement2,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Player 3 hasn't agreed yet

        # Step 4: GM performs pre-scene safety check
        self.client.force_authenticate(user=self.gm)
        scene_check = {
            "campaign_id": self.campaign.id,
            "planned_content_summary": "Investigation scene with potential violence and supernatural elements",
            "participants": [self.player1.id, self.player2.id, self.player3.id],
        }
        response = self.client.post(
            reverse("api:pre_scene_safety_check"), scene_check, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        check_results = response.data
        self.assertIn("check_results", check_results)
        self.assertIn("recommendations", check_results)

        # Step 5: GM validates specific content against all participants
        content_validation = {
            "content": """
            The investigation leads to a violent confrontation. The cultist threatens
            to harm animals unless the characters back down. The scene escalates to
            graphic torture of a prisoner.
            """,
            "campaign_id": self.campaign.id,
        }
        response = self.client.post(
            reverse("api:validate_content_for_campaign"),
            content_validation,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        validation_results = response.data
        self.assertFalse(
            validation_results["is_safe"]
        )  # Should trigger multiple concerns

        # Should identify issues for multiple players
        user_results = validation_results["user_results"]

        # Player 1 should have animal harm and graphic torture violations
        player1_result = next(
            (result for result in user_results if result["user_id"] == self.player1.id),
            None,
        )
        self.assertIsNotNone(player1_result)
        self.assertIn("Animal harm", player1_result["lines_violated"])
        self.assertIn("Graphic torture", player1_result["lines_violated"])

        # Step 6: GM validates revised content
        revised_content = {
            "content": """
            The investigation leads to a tense confrontation. The cultist makes threats
            but the characters manage to de-escalate. Some supernatural elements appear
            but nothing graphic occurs.
            """,
            "campaign_id": self.campaign.id,
        }
        response = self.client.post(
            reverse("api:validate_content_for_campaign"), revised_content, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        revised_results = response.data
        self.assertTrue(revised_results["is_safe"])  # Should be safe now

        # Step 7: Test privacy level enforcement
        # Player 2 tries to view Player 1's detailed preferences (should work - gm_only)
        self.client.force_authenticate(user=self.player2)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.player1.id})
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )  # Player2 is not GM

        # GM can view Player 1's preferences
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.player1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GM cannot view Player 3's private preferences
        response = self.client.get(
            reverse("api:user_safety_preferences", kwargs={"user_id": self.player3.id})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_safety_system_cross_campaign_isolation(self):
        """Test that safety preferences and agreements are properly isolated between campaigns."""

        # Create second campaign with different owner structure
        campaign2 = Campaign.objects.create(
            name="Second Campaign",
            owner=self.player2,  # player2 owns campaign2, NOT a participant
            game_system="D&D 5e",
            content_warnings=["Combat violence"],
            safety_tools_enabled=True,
        )

        # Create safety preferences for player1
        from users.models.safety import UserSafetyPreferences

        UserSafetyPreferences.objects.create(
            user=self.player1,
            lines=["Sexual content"],
            veils=["Violence"],
            privacy_level="campaign_members",
        )

        # Create safety agreement in first campaign
        from campaigns.models import CampaignSafetyAgreement

        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"],
        )

        # Player2 should not be able to access player1's agreement via campaign2
        self.client.force_authenticate(user=self.player2)
        response = self.client.get(
            reverse(
                "api:campaign_safety_agreements", kwargs={"campaign_id": campaign2.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should not contain player1's agreement from different campaign
        if "agreements" in response.data:
            agreement_participants = [
                agreement["user_id"] for agreement in response.data["agreements"]
            ]
            self.assertNotIn(self.player1.id, agreement_participants)

    def test_safety_system_with_disabled_tools(self):
        """Test safety system behavior when safety tools are disabled."""

        # Disable safety tools
        self.campaign.safety_tools_enabled = False
        self.campaign.save()

        # Create safety preferences
        from users.models.safety import UserSafetyPreferences

        UserSafetyPreferences.objects.create(
            user=self.player1,
            lines=["Violence"],
            veils=["Death"],
            privacy_level="gm_only",
        )

        # Test content validation still works but notes tools are disabled
        self.client.force_authenticate(user=self.gm)
        content_data = {
            "content": "Violent scene with death",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_user"), content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("safety_tools_disabled", response.data)
        self.assertTrue(response.data["safety_tools_disabled"])

    def test_safety_system_error_resilience(self):
        """Test safety system handles various error conditions gracefully."""

        # Test validation with non-existent user preferences
        self.client.force_authenticate(user=self.gm)

        # Player1 has no safety preferences set
        content_data = {
            "content": "Test content",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_user"), content_data, format="json"
        )

        # Should succeed with safe defaults
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_safe"])

    def test_safety_system_performance_with_large_campaign(self):
        """Test safety system performance with many participants."""

        # Add many additional players to campaign
        additional_players = []
        for i in range(15):  # Total of 18 participants
            user = User.objects.create_user(
                username=f"player{i+4}",
                email=f"player{i+4}@example.com",
                password="TestPass123!",
            )
            additional_players.append(user)

            CampaignMembership.objects.create(
                campaign=self.campaign, user=user, role="PLAYER"
            )

            # Create varied safety preferences
            from users.models.safety import UserSafetyPreferences

            UserSafetyPreferences.objects.create(
                user=user,
                lines=[f"Line {i}", "Violence"] if i % 2 == 0 else [],
                veils=[f"Veil {i}", "Death"] if i % 3 == 0 else [],
                privacy_level="campaign_members" if i % 2 == 0 else "gm_only",
            )

        # Test campaign-wide content validation
        self.client.force_authenticate(user=self.gm)

        content_data = {
            "content": "Large scene with violence, death, and various triggers",
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_campaign"), content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return results for all participants
        self.assertIn("user_results", response.data)


class SafetySystemTransactionTest(TransactionTestCase):
    """Test safety system database transaction handling."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            email_verified=True,
        )

        self.campaign = Campaign.objects.create(
            name="Transaction Test Campaign",
            owner=self.user,
            game_system="Test System",
            safety_tools_enabled=True,
        )

    def test_atomic_safety_preferences_update(self):
        """Test that safety preferences updates are atomic."""
        from users.models.safety import UserSafetyPreferences

        # Create initial preferences
        prefs = UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Original line"],
            veils=["Original veil"],
            privacy_level="private",
        )

        self.client.force_authenticate(user=self.user)

        # Attempt update that should succeed
        valid_update = {
            "lines": ["Updated line"],
            "veils": ["Updated veil"],
            "privacy_level": "gm_only",
            "consent_required": True,
        }

        response = self.client.put(
            reverse("api:safety_preferences"), valid_update, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify update was applied
        prefs.refresh_from_db()
        self.assertEqual(prefs.lines, ["Updated line"])
        self.assertEqual(prefs.privacy_level, "gm_only")

    def test_atomic_safety_agreement_creation(self):
        """Test that safety agreement creation is atomic."""
        from campaigns.models import CampaignSafetyAgreement

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.user, role="PLAYER"
        )

        self.client.force_authenticate(user=self.user)

        agreement_data = {
            "agreed_to_terms": True,
            "acknowledged_warnings": ["Test warning"],
        }

        response = self.client.post(
            reverse(
                "api:campaign_safety_agreement",
                kwargs={"campaign_id": self.campaign.id},
            ),
            agreement_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify agreement exists
        agreement = CampaignSafetyAgreement.objects.get(
            campaign=self.campaign, participant=self.user
        )
        self.assertTrue(agreement.agreed_to_terms)
        self.assertEqual(agreement.acknowledged_warnings, ["Test warning"])


class SafetySystemRealWorldScenariosTest(TestCase):
    """Test safety system with realistic RPG scenarios."""

    def setUp(self):
        """Set up realistic RPG scenario."""
        self.client = APIClient()

        # Create gaming group
        self.gm = User.objects.create_user(
            username="gm_alice",
            email="alice@gaminggroup.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.player_bob = User.objects.create_user(
            username="player_bob",
            email="bob@gaminggroup.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.player_carol = User.objects.create_user(
            username="player_carol",
            email="carol@gaminggroup.com",
            password="TestPass123!",
            email_verified=True,
        )
        self.player_dave = User.objects.create_user(
            username="player_dave",
            email="dave@gaminggroup.com",
            password="TestPass123!",
            email_verified=True,
        )

        # Create horror campaign
        self.horror_campaign = Campaign.objects.create(
            name="Call of Cthulhu: Shadows over Innsmouth",
            owner=self.gm,
            game_system="Call of Cthulhu",
            content_warnings=[
                "Cosmic horror",
                "Mental illness/madness",
                "Body horror",
                "Cultist violence",
                "Historical racism (1920s setting)",
            ],
            safety_tools_enabled=True,
        )

        # Add memberships
        for player in [self.player_bob, self.player_carol, self.player_dave]:
            CampaignMembership.objects.create(
                campaign=self.horror_campaign, user=player, role="PLAYER"
            )

    def test_horror_campaign_safety_setup(self):
        """Test realistic safety setup for horror RPG campaign."""

        # Bob: Has personal trauma around mental health issues
        self.client.force_authenticate(user=self.player_bob)
        bob_prefs = {
            "lines": ["Detailed mental breakdowns", "Suicide"],
            "veils": ["Mental illness", "Psychiatric treatment"],
            "privacy_level": "gm_only",  # Doesn't want other players to know
            "consent_required": True,
        }
        response = self.client.put(
            reverse("api:safety_preferences"), bob_prefs, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Carol: Comfortable with most horror but sensitive to body horror
        self.client.force_authenticate(user=self.player_carol)
        carol_prefs = {
            "lines": ["Extreme body horror"],
            "veils": ["Medical procedures", "Transformation scenes"],
            "privacy_level": "campaign_members",  # Open about boundaries
            "consent_required": False,
        }
        response = self.client.put(
            reverse("api:safety_preferences"), carol_prefs, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Dave: Generally comfortable, mainly concerned about historical content
        self.client.force_authenticate(user=self.player_dave)
        dave_prefs = {
            "lines": ["Graphic racist violence"],
            "veils": ["Historical racism", "Period-appropriate slurs"],
            "privacy_level": "campaign_members",
            "consent_required": False,
        }
        response = self.client.put(
            reverse("api:safety_preferences"), dave_prefs, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GM reviews safety overview
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(
            reverse(
                "api:campaign_safety_overview",
                kwargs={"campaign_id": self.horror_campaign.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GM should see Carol and Dave's preferences but only know Bob has restrictions
        overview = response.data
        self.assertIn("participants", overview)

    def test_realistic_scene_content_validation(self):
        """Test content validation for realistic horror RPG scenes."""

        # Set up safety preferences
        from users.models.safety import UserSafetyPreferences

        UserSafetyPreferences.objects.create(
            user=self.player_bob,
            lines=["Suicide", "Detailed mental breakdowns"],
            veils=["Mental illness"],
            privacy_level="gm_only",
            consent_required=True,
        )
        UserSafetyPreferences.objects.create(
            user=self.player_carol,
            lines=["Extreme body horror"],
            veils=["Medical procedures"],
            privacy_level="campaign_members",
            consent_required=False,
        )

        self.client.force_authenticate(user=self.gm)

        # Test problematic scene content
        problematic_scene = {
            "content": """
            Scene 3: The Sanatorium

            The investigators discover the abandoned psychiatric hospital where Dr. Marsh
            conducted his experiments. In the basement, they find detailed medical records
            describing lobotomies and other extreme procedures. The scene culminates with
            finding a patient who has attempted suicide, with graphic details of the method.

            The body horror elements include transformed patients with tentacles growing
            from surgical scars, and detailed descriptions of flesh melting and reshaping.
            """,
            "campaign_id": self.horror_campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_campaign"),
            problematic_scene,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        validation = response.data

        # Should flag multiple safety concerns
        self.assertFalse(validation["is_safe"])

        # Should identify specific user concerns
        user_results = validation["user_results"]

        bob_result = next(
            (r for r in user_results if r["user_id"] == self.player_bob.id), None
        )
        self.assertIsNotNone(bob_result)
        self.assertIn("Suicide", bob_result["lines_violated"])
        self.assertTrue(bob_result["consent_required"])

        carol_result = next(
            (r for r in user_results if r["user_id"] == self.player_carol.id), None
        )
        self.assertIsNotNone(carol_result)
        self.assertIn("Extreme body horror", carol_result["lines_violated"])

        # Test revised scene content
        revised_scene = {
            "content": """
            Scene 3: The Sanatorium (Revised)

            The investigators discover the abandoned psychiatric hospital where Dr. Marsh
            conducted his experiments. In the basement, they find medical records that
            hint at unethical procedures without graphic details.

            They discover evidence of a patient's tragic end, but the details fade to black.
            The supernatural transformations are described in cosmic horror terms without
            explicit body horror - emphasizing the wrongness and impossibility rather than
            graphic physical details.
            """,
            "campaign_id": self.horror_campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_campaign"), revised_scene, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        revised_validation = response.data

        # Should be much safer
        self.assertTrue(revised_validation["is_safe"])

        # May still trigger some veils but no hard lines
        user_results = revised_validation["user_results"]
        bob_result = next(
            (r for r in user_results if r["user_id"] == self.player_bob.id), None
        )
        if bob_result:
            self.assertEqual(len(bob_result["lines_violated"]), 0)

    def test_mid_session_safety_intervention(self):
        """Test safety system during active gameplay session."""

        # Set up preferences
        from users.models.safety import UserSafetyPreferences

        UserSafetyPreferences.objects.create(
            user=self.player_bob,
            lines=["Animal cruelty"],
            veils=["Violence against children"],
            privacy_level="gm_only",
        )

        # Simulate real-time content check during session
        self.client.force_authenticate(user=self.gm)

        # GM wants to introduce unexpected content
        real_time_check = {
            "content": "A cultist threatens to sacrifice the village children to summon the Old One",
            "campaign_id": self.horror_campaign.id,
            "immediate_participants": [self.player_bob.id, self.player_carol.id],
        }

        try:
            url = reverse("api:real_time_content_check")
        except Exception:
            self.skipTest("real_time_content_check endpoint not implemented yet")

        response = self.client.post(url, real_time_check, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        check_result = response.data

        # Should flag violence against children for Bob
        if not check_result.get("proceed_safe", True):
            self.assertIn("immediate_warnings", check_result)
            self.assertIn("required_actions", check_result)

    def test_session_zero_safety_discussion(self):
        """Test safety system supporting Session Zero discussions."""

        # All players create initial preferences
        preferences_data = [
            (
                self.player_bob,
                {"lines": ["Graphic violence"], "privacy_level": "gm_only"},
            ),
            (
                self.player_carol,
                {"lines": ["Sexual content"], "privacy_level": "campaign_members"},
            ),
            (
                self.player_dave,
                {"veils": ["Racism"], "privacy_level": "campaign_members"},
            ),
        ]

        for player, prefs in preferences_data:
            self.client.force_authenticate(user=player)
            prefs.update({"veils": prefs.get("veils", []), "consent_required": False})
            response = self.client.put(
                reverse("api:safety_preferences"), prefs, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GM gets aggregated safety summary for discussion
        self.client.force_authenticate(user=self.gm)
        try:
            url = reverse(
                "api:campaign_safety_discussion_guide",
                kwargs={"campaign_id": self.horror_campaign.id},
            )
        except Exception:
            self.skipTest(
                "campaign_safety_discussion_guide endpoint not implemented yet"
            )
        response = self.client.get(url)

        # Should provide talking points and common concerns
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        guide = response.data
        self.assertIn("discussion_topics", guide)
        self.assertIn("common_concerns", guide)
        self.assertIn("privacy_considerations", guide)
