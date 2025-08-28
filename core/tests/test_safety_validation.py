"""Test cases for safety validation system and content checking logic."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch, MagicMock

from campaigns.models import Campaign

User = get_user_model()


class SafetyValidationServiceTest(TestCase):
    """Test the safety validation service logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.gm,
            game_system="Mage: The Ascension",
            content_warnings=["Violence", "Supernatural themes"],
            safety_tools_enabled=True
        )

    def test_content_validation_against_lines(self):
        """Test content validation against user's hard boundaries (lines)."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create user safety preferences with lines
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sexual content", "Animal harm", "Graphic torture"],
            veils=["Violence"],
            privacy_level='gm_only'
        )
        
        validator = SafetyValidationService()
        
        # Test content that violates lines
        result = validator.validate_content(
            content="This scene contains graphic torture and violence.",
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertFalse(result['is_safe'])
        self.assertIn('lines_violated', result)
        self.assertIn('Graphic torture', result['lines_violated'])

    def test_content_validation_against_veils(self):
        """Test content validation against user's fade-to-black content (veils)."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create user safety preferences with veils
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sexual content"],
            veils=["Violence", "Death scenes", "Mental illness"],
            privacy_level='gm_only'
        )
        
        validator = SafetyValidationService()
        
        # Test content that triggers veils
        result = validator.validate_content(
            content="The character experiences a violent death scene.",
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertTrue(result['is_safe'])  # Veils don't make content unsafe, just flagged
        self.assertIn('veils_triggered', result)
        self.assertIn('Violence', result['veils_triggered'])
        self.assertIn('Death scenes', result['veils_triggered'])

    def test_content_validation_no_violations(self):
        """Test content validation with no safety violations."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create user safety preferences
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sexual content", "Animal harm"],
            veils=["Graphic violence"],
            privacy_level='gm_only'
        )
        
        validator = SafetyValidationService()
        
        # Test safe content
        result = validator.validate_content(
            content="The characters have a friendly conversation at the tavern.",
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertTrue(result['is_safe'])
        self.assertEqual(result['lines_violated'], [])
        self.assertEqual(result['veils_triggered'], [])

    def test_content_validation_multiple_users(self):
        """Test content validation against multiple users' preferences."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create second user
        user2 = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="testpass123"
        )
        
        # Create different safety preferences for each user
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sexual content"],
            veils=["Violence"],
            privacy_level='campaign_members'
        )
        UserSafetyPreferences.objects.create(
            user=user2,
            lines=["Animal harm"],
            veils=["Death"],
            privacy_level='campaign_members'
        )
        
        validator = SafetyValidationService()
        
        # Test content that affects both users differently
        result = validator.validate_content_for_campaign(
            content="A violent scene where animals are harmed.",
            campaign=self.campaign
        )
        
        self.assertFalse(result['is_safe'])
        self.assertIn(self.user.username, result['user_results'])
        self.assertIn(user2.username, result['user_results'])
        
        # User1 should have violence as veil triggered
        user1_result = result['user_results'][self.user.username]
        self.assertIn('Violence', user1_result['veils_triggered'])
        
        # User2 should have animal harm as line violated
        user2_result = result['user_results'][user2.username]
        self.assertIn('Animal harm', user2_result['lines_violated'])

    def test_content_validation_privacy_levels(self):
        """Test that privacy levels are respected during validation."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create user with private safety preferences
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Private content"],
            veils=["Private veil"],
            privacy_level='private'  # Should not be accessible to GM
        )
        
        validator = SafetyValidationService()
        
        # Test validation as GM - should not access private preferences
        result = validator.validate_content(
            content="This contains private content.",
            user=self.user,
            campaign=self.campaign,
            requesting_user=self.gm
        )
        
        # Should indicate privacy restriction
        self.assertTrue(result['privacy_restricted'])
        self.assertIn('message', result)

    def test_content_validation_consent_required(self):
        """Test validation when user requires explicit consent."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create user requiring consent
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Triggering content"],
            veils=["Sensitive content"],
            consent_required=True,
            privacy_level='gm_only'
        )
        
        validator = SafetyValidationService()
        
        # Test content that would trigger consent requirement
        result = validator.validate_content(
            content="This scene contains sensitive content.",
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertTrue(result['consent_required'])
        self.assertIn('Sensitive content', result['veils_triggered'])

    def test_content_validation_with_campaign_warnings(self):
        """Test validation considering campaign content warnings."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create user preferences that conflict with campaign warnings
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Violence"],  # Campaign has "Violence" in content_warnings
            veils=["Supernatural themes"],  # Campaign has this too
            privacy_level='gm_only'
        )
        
        validator = SafetyValidationService()
        
        # Test validation against campaign with conflicting warnings
        result = validator.check_campaign_compatibility(
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertFalse(result['is_compatible'])
        self.assertIn('conflicts', result)
        self.assertIn('Violence', result['conflicts']['lines'])
        self.assertIn('Supernatural themes', result['conflicts']['veils'])

    def test_safety_check_workflow_pre_scene(self):
        """Test pre-scene safety check workflow."""
        from users.models.safety import UserSafetyPreferences
        from campaigns.models import CampaignSafetyAgreement
        from core.services.safety import SafetyValidationService
        
        # Create user preferences and safety agreement
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Extreme violence"],
            veils=["Mental health issues"],
            privacy_level='campaign_members'
        )
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.user,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence", "Supernatural themes"]
        )
        
        validator = SafetyValidationService()
        
        # Test pre-scene safety check
        result = validator.pre_scene_safety_check(
            campaign=self.campaign,
            planned_content_summary="Scene involving supernatural investigation with mild violence"
        )
        
        self.assertTrue(result['check_passed'])
        self.assertIn('participant_status', result)
        self.assertIn(self.user.username, result['participant_status'])

    def test_safety_warning_generation(self):
        """Test generation of safety warnings for content."""
        from core.services.safety import SafetyValidationService
        
        validator = SafetyValidationService()
        
        # Test warning generation for potentially triggering content
        warnings = validator.generate_content_warnings(
            content="This scene contains violence, death, and supernatural horror themes."
        )
        
        self.assertIsInstance(warnings, list)
        self.assertGreater(len(warnings), 0)
        # Should detect violence, death, and horror themes
        warning_text = ' '.join(warnings).lower()
        self.assertIn('violence', warning_text)

    def test_gm_safety_management_tools(self):
        """Test GM tools for safety management."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Create multiple users with different preferences
        user2 = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="testpass123"
        )
        
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Sexual content"],
            veils=["Violence"],
            privacy_level='gm_only'
        )
        UserSafetyPreferences.objects.create(
            user=user2,
            lines=["Animal harm"],
            veils=["Mental illness"],
            privacy_level='campaign_members'
        )
        
        validator = SafetyValidationService()
        
        # Test GM safety overview
        overview = validator.get_campaign_safety_overview(
            campaign=self.campaign,
            requesting_user=self.gm
        )
        
        self.assertIn('participants', overview)
        self.assertIn('common_concerns', overview)
        self.assertIn('privacy_summary', overview)

    def test_real_time_safety_warning_system(self):
        """Test real-time safety warning generation."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Graphic torture"],
            veils=["Character death"],
            privacy_level='campaign_members'
        )
        
        validator = SafetyValidationService()
        
        # Test real-time content checking
        result = validator.real_time_content_check(
            content="The villain begins torturing the prisoner, leading to their death.",
            campaign=self.campaign,
            immediate_participants=[self.user]
        )
        
        self.assertFalse(result['proceed_safe'])
        self.assertIn('immediate_warnings', result)
        self.assertIn('required_actions', result)

    @patch('core.services.safety.SafetyValidationService._detect_content_themes')
    def test_content_theme_detection_mocked(self, mock_detect):
        """Test content theme detection with mocked AI/NLP service."""
        from core.services.safety import SafetyValidationService
        
        # Mock the theme detection to return specific themes
        mock_detect.return_value = ['violence', 'supernatural', 'mental_health']
        
        validator = SafetyValidationService()
        
        themes = validator._detect_content_themes("Test content")
        
        self.assertEqual(themes, ['violence', 'supernatural', 'mental_health'])
        mock_detect.assert_called_once_with("Test content")

    def test_safety_validation_edge_cases(self):
        """Test edge cases in safety validation."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        validator = SafetyValidationService()
        
        # Test with user who has no safety preferences
        result = validator.validate_content(
            content="Some content",
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertTrue(result['is_safe'])
        self.assertEqual(result['lines_violated'], [])
        self.assertEqual(result['veils_triggered'], [])

    def test_safety_validation_empty_content(self):
        """Test safety validation with empty or None content."""
        from core.services.safety import SafetyValidationService
        
        validator = SafetyValidationService()
        
        # Test empty content
        result = validator.validate_content(
            content="",
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertTrue(result['is_safe'])
        
        # Test None content
        result = validator.validate_content(
            content=None,
            user=self.user,
            campaign=self.campaign
        )
        
        self.assertTrue(result['is_safe'])

    def test_safety_validation_campaign_safety_disabled(self):
        """Test behavior when campaign has safety tools disabled."""
        from users.models.safety import UserSafetyPreferences
        from core.services.safety import SafetyValidationService
        
        # Disable safety tools for campaign
        self.campaign.safety_tools_enabled = False
        self.campaign.save()
        
        UserSafetyPreferences.objects.create(
            user=self.user,
            lines=["Violence"],
            veils=["Death"],
            privacy_level='gm_only'
        )
        
        validator = SafetyValidationService()
        
        # Test validation with safety tools disabled
        result = validator.validate_content(
            content="Violent content with death",
            user=self.user,
            campaign=self.campaign
        )
        
        # Should still respect individual preferences but note tools are disabled
        self.assertIn('safety_tools_disabled', result)
        self.assertTrue(result['safety_tools_disabled'])


class SafetyValidationUtilsTest(TestCase):
    """Test utility functions for safety validation."""

    def test_content_keyword_matching(self):
        """Test keyword matching for content analysis."""
        from core.utils.safety import ContentAnalyzer
        
        analyzer = ContentAnalyzer()
        
        # Test violence keywords
        violence_content = "The character attacks with a sword, causing bloodshed."
        violence_matches = analyzer.find_keyword_matches(
            violence_content, 
            keyword_category='violence'
        )
        
        self.assertGreater(len(violence_matches), 0)
        self.assertIn('attacks', violence_matches)

    def test_content_sentiment_analysis(self):
        """Test content sentiment analysis for safety assessment."""
        from core.utils.safety import ContentAnalyzer
        
        analyzer = ContentAnalyzer()
        
        # Test dark/disturbing content
        dark_content = "The scene is filled with despair, torture, and hopelessness."
        sentiment = analyzer.analyze_sentiment(dark_content)
        
        self.assertIn('sentiment_score', sentiment)
        self.assertIn('emotional_intensity', sentiment)
        self.assertLess(sentiment['sentiment_score'], 0)  # Should be negative

    def test_privacy_level_access_control(self):
        """Test privacy level access control logic."""
        from core.utils.safety import PrivacyController
        
        controller = PrivacyController()
        
        # Test different privacy scenarios
        test_cases = [
            ('private', 'gm', False),  # GM cannot access private
            ('private', 'owner', False),  # Owner cannot access private
            ('private', 'user', True),  # User can access own private
            ('gm_only', 'gm', True),   # GM can access gm_only
            ('gm_only', 'owner', True), # Owner can access gm_only
            ('gm_only', 'player', False), # Player cannot access gm_only
            ('campaign_members', 'player', True), # Player can access campaign_members
        ]
        
        for privacy_level, requester_role, expected_access in test_cases:
            with self.subTest(privacy=privacy_level, role=requester_role):
                has_access = controller.can_access_preferences(
                    privacy_level=privacy_level,
                    requester_role=requester_role,
                    is_preferences_owner=(requester_role == 'user')
                )
                self.assertEqual(has_access, expected_access)

    def test_safety_theme_categorization(self):
        """Test categorization of detected safety themes."""
        from core.utils.safety import SafetyThemeClassifier
        
        classifier = SafetyThemeClassifier()
        
        themes = ['violence', 'sexual_content', 'mental_health', 'animal_harm', 'death']
        categorized = classifier.categorize_themes(themes)
        
        self.assertIn('high_severity', categorized)
        self.assertIn('medium_severity', categorized)
        self.assertIn('requires_consent', categorized)
        
        # Sexual content and animal harm should be high severity
        self.assertIn('sexual_content', categorized['high_severity'])
        self.assertIn('animal_harm', categorized['high_severity'])

    def test_content_warning_message_generation(self):
        """Test generation of user-friendly content warning messages."""
        from core.utils.safety import WarningMessageGenerator
        
        generator = WarningMessageGenerator()
        
        # Test warning message for lines violation
        lines_message = generator.generate_lines_warning(
            violated_lines=['Sexual content', 'Animal harm'],
            user_name='TestUser'
        )
        
        self.assertIn('hard boundary', lines_message.lower())
        self.assertIn('testuser', lines_message.lower())
        self.assertIn('sexual content', lines_message.lower())

    def test_safety_audit_logging(self):
        """Test safety validation audit logging."""
        from core.utils.safety import SafetyAuditLogger
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        logger = SafetyAuditLogger()
        
        # Test logging a safety validation event
        log_entry = logger.log_safety_check(
            campaign=self.campaign,
            user=self.user,
            content_summary="Test scene with violence",
            validation_result={
                'is_safe': False,
                'lines_violated': ['Violence'],
                'veils_triggered': []
            },
            action_taken='content_blocked'
        )
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry['campaign_id'], self.campaign.id)
        self.assertEqual(log_entry['user_id'], self.user.id)
        self.assertEqual(log_entry['action_taken'], 'content_blocked')