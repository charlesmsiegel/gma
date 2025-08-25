"""
Comprehensive tests for the requirement checking engine (Issue #189).

This module tests the check_requirement function that validates whether a character
meets specific requirements defined in JSON format.

Test coverage:
1. Trait requirements with getattr checking
2. Has requirements with ORM relationship checking
3. Logical requirements (any/all) with recursion
4. Count tag requirements for counting objects
5. Extensible custom requirement types
6. Error handling and edge cases
7. Performance optimization
8. Integration with existing Character models

The tests use the polymorphic Character model hierarchy and validate that
the checking engine works correctly with all character types.
"""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character, MageCharacter, WoDCharacter
from prerequisites.checkers import (
    RequirementCheckResult,
    check_requirement,
    get_registered_checker_types,
    register_requirement_checker,
    unregister_requirement_checker,
)
from prerequisites.helpers import all_of, any_of, count_with_tag, has_item, trait_req
from users.models import User


class RequirementCheckResultTest(TestCase):
    """Test RequirementCheckResult data structure."""

    def test_successful_result_creation(self):
        """Test creating a successful requirement check result."""
        result = RequirementCheckResult(
            success=True,
            message="Requirement met",
            details={"checked_trait": "strength", "value": 4},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Requirement met")
        self.assertEqual(result.details["checked_trait"], "strength")
        self.assertEqual(result.details["value"], 4)

    def test_failed_result_creation(self):
        """Test creating a failed requirement check result."""
        result = RequirementCheckResult(
            success=False,
            message="Insufficient strength",
            details={"required": 5, "actual": 3},
        )

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Insufficient strength")
        self.assertEqual(result.details["required"], 5)
        self.assertEqual(result.details["actual"], 3)

    def test_result_str_representation(self):
        """Test string representation of results."""
        success_result = RequirementCheckResult(success=True, message="Requirement met")
        fail_result = RequirementCheckResult(
            success=False, message="Requirement not met"
        )

        self.assertEqual(str(success_result), "SUCCESS: Requirement met")
        self.assertEqual(str(fail_result), "FAILED: Requirement not met")

    def test_result_bool_conversion(self):
        """Test boolean conversion of results."""
        success_result = RequirementCheckResult(success=True, message="Success")
        fail_result = RequirementCheckResult(success=False, message="Failed")

        self.assertTrue(success_result)
        self.assertFalse(fail_result)


class TraitRequirementCheckingTest(TestCase):
    """Test trait requirement checking functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        # Create a Mage character with specific trait values
        self.character = MageCharacter.objects.create(
            name="Test Mage",
            description="Test character for requirement checking",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            arete=3,
            quintessence=5,
            paradox=1,
            willpower=6,
        )

    def test_trait_minimum_requirement_success(self):
        """Test successful trait minimum requirement check."""
        requirement = trait_req("arete", minimum=2)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertIn("arete", result.message)
        self.assertEqual(result.details["trait_name"], "arete")
        self.assertEqual(result.details["actual_value"], 3)
        self.assertEqual(result.details["required_minimum"], 2)

    def test_trait_minimum_requirement_failure(self):
        """Test failed trait minimum requirement check."""
        requirement = trait_req("arete", minimum=5)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("insufficient", result.message.lower())
        self.assertEqual(result.details["trait_name"], "arete")
        self.assertEqual(result.details["actual_value"], 3)
        self.assertEqual(result.details["required_minimum"], 5)

    def test_trait_maximum_requirement_success(self):
        """Test successful trait maximum requirement check."""
        requirement = trait_req("paradox", maximum=3)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertIn("paradox", result.message)
        self.assertEqual(result.details["actual_value"], 1)
        self.assertEqual(result.details["required_maximum"], 3)

    def test_trait_maximum_requirement_failure(self):
        """Test failed trait maximum requirement check."""
        requirement = trait_req("willpower", maximum=4)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("exceeds maximum", result.message.lower())
        self.assertEqual(result.details["actual_value"], 6)
        self.assertEqual(result.details["required_maximum"], 4)

    def test_trait_exact_requirement_success(self):
        """Test successful trait exact requirement check."""
        requirement = trait_req("quintessence", exact=5)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.details["actual_value"], 5)
        self.assertEqual(result.details["required_exact"], 5)

    def test_trait_exact_requirement_failure(self):
        """Test failed trait exact requirement check."""
        requirement = trait_req("arete", exact=2)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("must be exactly", result.message.lower())
        self.assertEqual(result.details["actual_value"], 3)
        self.assertEqual(result.details["required_exact"], 2)

    def test_trait_min_max_requirement_success(self):
        """Test successful trait min/max range requirement."""
        requirement = trait_req("willpower", minimum=5, maximum=8)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.details["actual_value"], 6)
        self.assertEqual(result.details["required_minimum"], 5)
        self.assertEqual(result.details["required_maximum"], 8)

    def test_trait_min_max_requirement_below_range(self):
        """Test trait requirement below minimum in range."""
        requirement = trait_req("arete", minimum=5, maximum=8)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("insufficient", result.message.lower())
        self.assertEqual(result.details["actual_value"], 3)

    def test_trait_min_max_requirement_above_range(self):
        """Test trait requirement above maximum in range."""
        requirement = trait_req("willpower", minimum=1, maximum=4)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("exceeds maximum", result.message.lower())
        self.assertEqual(result.details["actual_value"], 6)

    def test_trait_nonexistent_attribute(self):
        """Test trait requirement for non-existent attribute."""
        requirement = trait_req("nonexistent_attr", minimum=1)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("does not have trait", result.message.lower())
        self.assertEqual(result.details["actual_value"], 0)

    def test_trait_default_value_behavior(self):
        """Test that getattr returns 0 for non-existent traits."""
        requirement = trait_req("missing_trait", minimum=0)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.details["actual_value"], 0)


class HasRequirementCheckingTest(TestCase):
    """Test has requirement checking functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = Character.objects.create(
            name="Test Character",
            description="Test character for has requirements",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Generic",
        )

    @patch("prerequisites.checkers._check_has_requirement_orm")
    def test_has_requirement_by_id_success(self, mock_orm_check):
        """Test successful has requirement check by ID."""
        mock_orm_check.return_value = True

        requirement = has_item("weapons", id=123)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertIn("has required", result.message.lower())
        self.assertEqual(result.details["field"], "weapons")
        self.assertEqual(result.details["id"], 123)

        mock_orm_check.assert_called_once_with(self.character, "weapons", {"id": 123})

    @patch("prerequisites.checkers._check_has_requirement_orm")
    def test_has_requirement_by_id_failure(self, mock_orm_check):
        """Test failed has requirement check by ID."""
        mock_orm_check.return_value = False

        requirement = has_item("weapons", id=456)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("does not have required", result.message.lower())
        self.assertEqual(result.details["field"], "weapons")
        self.assertEqual(result.details["id"], 456)

    @patch("prerequisites.checkers._check_has_requirement_orm")
    def test_has_requirement_by_name_success(self, mock_orm_check):
        """Test successful has requirement check by name."""
        mock_orm_check.return_value = True

        requirement = has_item("foci", name="Crystal Orb")
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.details["field"], "foci")
        self.assertEqual(result.details["name"], "Crystal Orb")

    @patch("prerequisites.checkers._check_has_requirement_orm")
    def test_has_requirement_by_name_failure(self, mock_orm_check):
        """Test failed has requirement check by name."""
        mock_orm_check.return_value = False

        requirement = has_item("talismans", name="Missing Item")
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("does not have required", result.message.lower())

    @patch("prerequisites.checkers._check_has_requirement_orm")
    def test_has_requirement_with_additional_fields(self, mock_orm_check):
        """Test has requirement with additional fields."""
        mock_orm_check.return_value = True

        requirement = has_item("weapons", id=123, name="Magic Sword", level=3)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        mock_orm_check.assert_called_once_with(
            self.character, "weapons", {"id": 123, "name": "Magic Sword", "level": 3}
        )


class LogicalRequirementCheckingTest(TestCase):
    """Test any/all logical requirement checking with recursion."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = MageCharacter.objects.create(
            name="Test Mage",
            description="Test character for logical requirements",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            arete=3,
            willpower=4,
        )

    def test_any_requirement_success_first_matches(self):
        """Test any requirement where first sub-requirement matches."""
        requirement = any_of(
            trait_req("arete", minimum=2),  # This should pass (3 >= 2)
            trait_req("willpower", minimum=10),  # This would fail (4 < 10)
        )
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertIn("at least one requirement satisfied", result.message.lower())
        self.assertEqual(len(result.details["sub_results"]), 2)
        self.assertTrue(result.details["sub_results"][0]["success"])
        self.assertFalse(result.details["sub_results"][1]["success"])

    def test_any_requirement_success_second_matches(self):
        """Test any requirement where second sub-requirement matches."""
        requirement = any_of(
            trait_req("arete", minimum=5),  # This should fail (3 < 5)
            trait_req("willpower", minimum=3),  # This should pass (4 >= 3)
        )
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertFalse(result.details["sub_results"][0]["success"])
        self.assertTrue(result.details["sub_results"][1]["success"])

    def test_any_requirement_failure_none_match(self):
        """Test any requirement where no sub-requirements match."""
        requirement = any_of(
            trait_req("arete", minimum=5),  # Fails (3 < 5)
            trait_req("willpower", minimum=8),  # Fails (4 < 8)
        )
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("no requirements satisfied", result.message.lower())
        self.assertFalse(result.details["sub_results"][0]["success"])
        self.assertFalse(result.details["sub_results"][1]["success"])

    def test_all_requirement_success_all_match(self):
        """Test all requirement where all sub-requirements match."""
        requirement = all_of(
            trait_req("arete", minimum=2),  # Passes (3 >= 2)
            trait_req("willpower", minimum=3),  # Passes (4 >= 3)
        )
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertIn("all requirements satisfied", result.message.lower())
        self.assertTrue(result.details["sub_results"][0]["success"])
        self.assertTrue(result.details["sub_results"][1]["success"])

    def test_all_requirement_failure_one_fails(self):
        """Test all requirement where one sub-requirement fails."""
        requirement = all_of(
            trait_req("arete", minimum=2),  # Passes (3 >= 2)
            trait_req("willpower", minimum=8),  # Fails (4 < 8)
        )
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("not all requirements satisfied", result.message.lower())
        self.assertTrue(result.details["sub_results"][0]["success"])
        self.assertFalse(result.details["sub_results"][1]["success"])

    def test_nested_logical_requirements(self):
        """Test deeply nested logical requirements."""
        requirement = any_of(
            all_of(
                trait_req("arete", minimum=5),  # Fails
                trait_req("willpower", minimum=10),  # Fails
            ),
            all_of(
                trait_req("arete", minimum=2),  # Passes
                trait_req("willpower", minimum=3),  # Passes
            ),
        )
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        # The first all_of should fail, but the second should succeed
        self.assertFalse(result.details["sub_results"][0]["success"])
        self.assertTrue(result.details["sub_results"][1]["success"])

    def test_complex_nested_structure(self):
        """Test complex nested requirement structure."""
        requirement = all_of(
            trait_req("arete", minimum=1),  # Should pass
            any_of(
                trait_req("willpower", minimum=8),  # Will fail
                trait_req("willpower", minimum=3),  # Will pass
            ),
        )
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)


class CountTagRequirementCheckingTest(TestCase):
    """Test count_tag requirement checking functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = Character.objects.create(
            name="Test Character",
            description="Test character for count requirements",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Generic",
        )

    @patch("prerequisites.checkers._count_objects_with_tag")
    def test_count_tag_minimum_success(self, mock_count):
        """Test successful count_tag minimum requirement."""
        mock_count.return_value = 3

        requirement = count_with_tag("spheres", "elemental", minimum=2)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertIn("sufficient count", result.message.lower())
        self.assertEqual(result.details["model"], "spheres")
        self.assertEqual(result.details["tag"], "elemental")
        self.assertEqual(result.details["actual_count"], 3)
        self.assertEqual(result.details["required_minimum"], 2)

    @patch("prerequisites.checkers._count_objects_with_tag")
    def test_count_tag_minimum_failure(self, mock_count):
        """Test failed count_tag minimum requirement."""
        mock_count.return_value = 1

        requirement = count_with_tag("charms", "martial_arts", minimum=3)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("insufficient count", result.message.lower())
        self.assertEqual(result.details["actual_count"], 1)
        self.assertEqual(result.details["required_minimum"], 3)

    @patch("prerequisites.checkers._count_objects_with_tag")
    def test_count_tag_maximum_success(self, mock_count):
        """Test successful count_tag maximum requirement."""
        mock_count.return_value = 2

        requirement = count_with_tag("flaws", "mental", maximum=3)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.details["actual_count"], 2)
        self.assertEqual(result.details["required_maximum"], 3)

    @patch("prerequisites.checkers._count_objects_with_tag")
    def test_count_tag_maximum_failure(self, mock_count):
        """Test failed count_tag maximum requirement."""
        mock_count.return_value = 5

        requirement = count_with_tag("merits", "social", maximum=3)
        result = check_requirement(self.character, requirement)

        self.assertFalse(result.success)
        self.assertIn("exceeds maximum", result.message.lower())
        self.assertEqual(result.details["actual_count"], 5)
        self.assertEqual(result.details["required_maximum"], 3)

    @patch("prerequisites.checkers._count_objects_with_tag")
    def test_count_tag_range_success(self, mock_count):
        """Test successful count_tag range requirement."""
        mock_count.return_value = 3

        requirement = count_with_tag("abilities", "physical", minimum=2, maximum=5)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.details["actual_count"], 3)
        self.assertEqual(result.details["required_minimum"], 2)
        self.assertEqual(result.details["required_maximum"], 5)


class ExtensibleRequirementSystemTest(TestCase):
    """Test extensible system for custom requirement checkers."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = Character.objects.create(
            name="Test Character",
            description="Test character for custom requirements",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Generic",
        )

    def test_register_custom_requirement_checker(self):
        """Test registering a custom requirement checker."""

        def custom_checker(character, requirement_data):
            return RequirementCheckResult(
                success=True,
                message="Custom requirement passed",
                details={"custom": True},
            )

        # Register the custom checker
        register_requirement_checker("custom", custom_checker)

        # Verify it's registered
        self.assertIn("custom", get_registered_checker_types())

        # Test using the custom requirement
        requirement = {"custom": {"test": True}}
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Custom requirement passed")
        self.assertTrue(result.details["custom"])

        # Clean up
        unregister_requirement_checker("custom")

    def test_unregister_requirement_checker(self):
        """Test unregistering a requirement checker."""

        def custom_checker(character, requirement_data):
            return RequirementCheckResult(success=True, message="Custom")

        # Register then unregister
        register_requirement_checker("temporary", custom_checker)
        self.assertIn("temporary", get_registered_checker_types())

        result = unregister_requirement_checker("temporary")
        self.assertTrue(result)
        self.assertNotIn("temporary", get_registered_checker_types())

        # Try unregistering non-existent checker
        result = unregister_requirement_checker("nonexistent")
        self.assertFalse(result)

    def test_custom_checker_overrides_builtin(self):
        """Test that custom checkers can override built-in ones."""

        def custom_trait_checker(character, requirement_data):
            return RequirementCheckResult(
                success=True,
                message="Custom trait checker used",
                details={"overridden": True},
            )

        # Register custom trait checker
        register_requirement_checker("trait", custom_trait_checker)

        requirement = trait_req("strength", minimum=3)
        result = check_requirement(self.character, requirement)

        self.assertTrue(result.success)
        self.assertEqual(result.message, "Custom trait checker used")
        self.assertTrue(result.details["overridden"])

        # Restore original checker manually
        from prerequisites.checkers import _check_trait_requirement

        register_requirement_checker("trait", _check_trait_requirement)

    def test_get_registered_checker_types(self):
        """Test getting list of registered checker types."""
        types = get_registered_checker_types()

        # Should include all built-in types
        expected_types = {"trait", "has", "any", "all", "count_tag"}
        self.assertTrue(expected_types.issubset(set(types)))


class ErrorHandlingTest(TestCase):
    """Test error handling and edge cases in requirement checking."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = Character.objects.create(
            name="Test Character",
            description="Test character for error handling",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Generic",
        )

    def test_invalid_requirement_structure(self):
        """Test handling of invalid requirement structures."""
        with self.assertRaises(ValidationError):
            check_requirement(self.character, "not a dict")

        with self.assertRaises(ValidationError):
            check_requirement(self.character, {})

        with self.assertRaises(ValidationError):
            check_requirement(self.character, {"multiple": True, "types": True})

    def test_unknown_requirement_type(self):
        """Test handling of unknown requirement types."""
        with self.assertRaises(ValidationError) as cm:
            check_requirement(self.character, {"unknown_type": {"test": True}})

        self.assertIn("Unknown requirement type", str(cm.exception))

    def test_none_character(self):
        """Test handling of None character."""
        requirement = trait_req("strength", minimum=3)

        with self.assertRaises(ValidationError) as cm:
            check_requirement(None, requirement)

        self.assertIn("Character cannot be None", str(cm.exception))

    def test_none_requirement(self):
        """Test handling of None requirement."""
        with self.assertRaises(ValidationError) as cm:
            check_requirement(self.character, None)

        self.assertIn("Requirement cannot be None", str(cm.exception))

    def test_malformed_trait_requirement(self):
        """Test handling of malformed trait requirements."""
        # Missing required fields should be caught by validators during helper creation
        with self.assertRaises(ValidationError):
            trait_req("", minimum=3)  # Empty name

    def test_exception_in_custom_checker(self):
        """Test handling exceptions in custom checkers."""

        def failing_checker(character, requirement_data):
            raise Exception("Custom checker failed")

        register_requirement_checker("failing", failing_checker)

        with self.assertRaises(ValidationError) as cm:
            check_requirement(self.character, {"failing": {"test": True}})

        self.assertIn("Error checking requirement", str(cm.exception))
        self.assertIn("Custom checker failed", str(cm.exception))

        # Clean up
        unregister_requirement_checker("failing")


class PerformanceOptimizationTest(TestCase):
    """Test performance optimization aspects of requirement checking."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = MageCharacter.objects.create(
            name="Test Mage",
            description="Test character for performance testing",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            arete=3,
            willpower=5,
        )

    def test_deep_nesting_performance(self):
        """Test performance with deeply nested requirements."""
        # Create a 5-level deep nested structure
        requirement = any_of(
            all_of(
                any_of(
                    all_of(
                        trait_req("arete", minimum=1),
                        trait_req("willpower", minimum=1),
                    ),
                    trait_req("arete", minimum=10),
                ),
                trait_req("willpower", minimum=4),
            ),
            trait_req("arete", minimum=2),
        )

        # Should complete in reasonable time
        result = check_requirement(self.character, requirement)
        self.assertTrue(result.success)

    @patch("prerequisites.checkers._check_has_requirement_orm")
    def test_multiple_has_checks_efficiency(self, mock_orm_check):
        """Test that multiple has checks are handled efficiently."""
        mock_orm_check.return_value = True

        # Create requirement with multiple has checks
        requirement = all_of(
            has_item("weapons", id=1),
            has_item("armor", id=2),
            has_item("foci", id=3),
        )

        result = check_requirement(self.character, requirement)
        self.assertTrue(result.success)

        # Verify ORM method was called for each has check
        self.assertEqual(mock_orm_check.call_count, 3)


class IntegrationTest(TestCase):
    """Test integration with existing Character models and relationships."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

    def test_character_polymorphic_compatibility(self):
        """Test that checking works with all Character types."""
        # Test with base Character
        character = Character.objects.create(
            name="Base Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Generic",
        )

        requirement = trait_req("nonexistent", minimum=0)
        result = check_requirement(character, requirement)
        self.assertTrue(result.success)

        # Create a separate campaign for WoD character to avoid character limit
        wod_campaign = Campaign.objects.create(
            name="WoD Campaign", description="WoD Test", owner=self.user
        )

        # Test with WoDCharacter
        wod_char = WoDCharacter.objects.create(
            name="WoD Character",
            campaign=wod_campaign,
            player_owner=self.user,
            game_system="World of Darkness",
            willpower=6,
        )

        requirement = trait_req("willpower", minimum=5)
        result = check_requirement(wod_char, requirement)
        self.assertTrue(result.success)

        # Create another campaign for Mage character
        mage_campaign = Campaign.objects.create(
            name="Mage Campaign", description="Mage Test", owner=self.user
        )

        # Test with MageCharacter
        mage_char = MageCharacter.objects.create(
            name="Mage Character",
            campaign=mage_campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            willpower=5,
            arete=3,
            quintessence=4,
            paradox=1,
        )

        complex_requirement = all_of(
            trait_req("arete", minimum=2),
            trait_req("willpower", minimum=4),
            any_of(
                trait_req("quintessence", minimum=3),
                trait_req("paradox", maximum=2),
            ),
        )

        result = check_requirement(mage_char, complex_requirement)
        self.assertTrue(result.success)

    def test_realistic_requirement_scenario(self):
        """Test a realistic complex requirement scenario."""
        # Create a separate campaign for this test
        advanced_campaign = Campaign.objects.create(
            name="Advanced Campaign", description="Advanced Test", owner=self.user
        )
        
        mage = MageCharacter.objects.create(
            name="Advanced Mage",
            campaign=advanced_campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            willpower=7,
            arete=4,
            quintessence=8,
            paradox=2,
        )

        # Complex requirement: High-level spell prerequisites
        requirement = all_of(
            trait_req("arete", minimum=4),  # Must have Arete 4+
            trait_req("willpower", minimum=6),  # Must have Willpower 6+
            any_of(
                trait_req("quintessence", minimum=10),  # Either lots of Quintessence
                all_of(
                    trait_req("quintessence", minimum=5),  # Or moderate Quintessence
                    trait_req("paradox", maximum=3),  # With low Paradox
                ),
            ),
        )

        result = check_requirement(mage, requirement)
        self.assertTrue(result.success)

        # Verify detailed results
        details = result.details
        self.assertTrue(details["sub_results"][0]["success"])  # Arete check
        self.assertTrue(details["sub_results"][1]["success"])  # Willpower check
        self.assertTrue(details["sub_results"][2]["success"])  # Any check

        # The any check should succeed on the second alternative (moderate + low paradox)
        any_details = details["sub_results"][2]["details"]
        # Quintessence 10+
        self.assertFalse(any_details["sub_results"][0]["success"])
        # Moderate + low paradox
        self.assertTrue(any_details["sub_results"][1]["success"])


class HelperIntegrationTest(TestCase):
    """Test integration with helper functions from Issue #188."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", description="Test", owner=self.user
        )

        self.character = MageCharacter.objects.create(
            name="Test Mage",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
            arete=3,
            willpower=5,
            quintessence=2,
        )

    def test_helpers_generate_valid_requirements(self):
        """Test that all helpers generate requirements that work with checkers."""
        # Test all helper functions work with the checker
        trait_requirement = trait_req("arete", minimum=2)
        result = check_requirement(self.character, trait_requirement)
        self.assertTrue(result.success)

        # Has requirements (mocked)
        with patch(
            "prerequisites.checkers._check_has_requirement_orm", return_value=True
        ):
            has_requirement = has_item("weapons", id=123)
            result = check_requirement(self.character, has_requirement)
            self.assertTrue(result.success)

        # Logical requirements
        any_requirement = any_of(
            trait_req("arete", minimum=5),  # Will fail
            trait_req("willpower", minimum=4),  # Will pass
        )
        result = check_requirement(self.character, any_requirement)
        self.assertTrue(result.success)

        all_requirement = all_of(
            trait_req("arete", minimum=2),  # Will pass
            trait_req("willpower", minimum=4),  # Will pass
        )
        result = check_requirement(self.character, all_requirement)
        self.assertTrue(result.success)

        # Count requirements (mocked)
        with patch("prerequisites.checkers._count_objects_with_tag", return_value=3):
            count_requirement = count_with_tag("spheres", "elemental", minimum=2)
            result = check_requirement(self.character, count_requirement)
            self.assertTrue(result.success)
