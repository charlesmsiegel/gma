"""
Test the standardized error handling utilities.

This module tests the new error handling patterns to ensure they provide
consistent, security-focused responses.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from api.errors import (
    APIError,
    FieldValidator,
    SecurityResponseHelper,
    handle_django_validation_error,
)
from campaigns.models import Campaign, CampaignInvitation

User = get_user_model()


class APIErrorTests(TestCase):
    """Test the APIError utility class."""

    def test_not_found_response(self):
        """Test standard 404 response."""
        response = APIError.not_found()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

    def test_not_found_custom_message(self):
        """Test 404 response with custom message."""
        custom_message = "Custom not found message."
        response = APIError.not_found(custom_message)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], custom_message)

    def test_permission_denied_response(self):
        """Test standard 403 response."""
        response = APIError.create_permission_denied_response()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Permission denied.")

    def test_permission_denied_as_not_found(self):
        """Test permission denied disguised as 404 for security."""
        response = APIError.permission_denied_as_not_found()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

    def test_bad_request_response(self):
        """Test standard 400 response."""
        response = APIError.create_bad_request_response()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Bad request.")

    def test_validation_error_with_dict(self):
        """Test validation error with field-specific errors."""
        errors = {"username": ["This field is required."]}
        response = APIError.create_validation_error_response(errors)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, errors)

    def test_validation_error_with_string(self):
        """Test validation error with general message."""
        error_message = "General validation error."
        response = APIError.create_validation_error_response(error_message)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], error_message)

    def test_validation_error_with_django_exception(self):
        """Test validation error with Django ValidationError."""
        django_error = DjangoValidationError("Django validation failed.")
        response = APIError.create_validation_error_response(django_error)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Django validation failed.")

    def test_unauthorized_response(self):
        """Test standard 401 response."""
        response = APIError.create_unauthorized_response()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "Authentication required.")


class FieldValidatorTests(TestCase):
    """Test the FieldValidator utility class."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_required_field_with_value(self):
        """Test required field validation with valid value."""
        result = FieldValidator.required_field("username", "valid_username")
        self.assertIsNone(result)

    def test_required_field_without_value(self):
        """Test required field validation with missing value."""
        result = FieldValidator.required_field("username", "")
        expected = {"username": ["This field is required."]}
        self.assertEqual(result, expected)

    def test_required_field_with_none(self):
        """Test required field validation with None value."""
        result = FieldValidator.required_field("username", None)
        expected = {"username": ["This field is required."]}
        self.assertEqual(result, expected)

    def test_validate_user_exists_valid(self):
        """Test user validation with existing user."""
        result = FieldValidator.validate_user_exists(self.user.id)
        self.assertEqual(result, self.user)

    def test_validate_user_exists_invalid(self):
        """Test user validation with non-existent user."""
        result = FieldValidator.validate_user_exists(99999)
        self.assertIsNone(result)

    def test_validate_user_exists_empty(self):
        """Test user validation with empty value."""
        result = FieldValidator.validate_user_exists("")
        self.assertIsNone(result)

    def test_build_field_errors(self):
        """Test building field errors from keyword arguments."""
        result = FieldValidator.build_field_errors(
            username=["Username is required."], email="Invalid email format."
        )
        expected = {
            "username": ["Username is required."],
            "email": ["Invalid email format."],
        }
        self.assertEqual(result, expected)


class SecurityResponseHelperTests(TestCase):
    """Test the SecurityResponseHelper utility class."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="generic",
        )

    def test_resource_access_denied(self):
        """Test standard resource access denied response."""
        response = SecurityResponseHelper.resource_access_denied()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

    def test_safe_get_or_404_success(self):
        """Test safe get with existing object and permission."""
        obj, error_response = SecurityResponseHelper.safe_get_or_404(
            Campaign.objects,
            self.owner,
            lambda user, camp: user == camp.owner,
            id=self.campaign.id,
        )
        self.assertEqual(obj, self.campaign)
        self.assertIsNone(error_response)

    def test_safe_get_or_404_not_found(self):
        """Test safe get with non-existent object."""
        obj, error_response = SecurityResponseHelper.safe_get_or_404(
            Campaign.objects, self.user, id=99999
        )
        self.assertIsNone(obj)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_safe_get_or_404_permission_denied(self):
        """Test safe get with existing object but no permission."""
        obj, error_response = SecurityResponseHelper.safe_get_or_404(
            Campaign.objects,
            self.user,
            lambda user, camp: user == camp.owner,  # Permission check fails
            id=self.campaign.id,
        )
        self.assertIsNone(obj)
        self.assertIsNotNone(error_response)
        self.assertEqual(error_response.status_code, status.HTTP_404_NOT_FOUND)


class HandleDjangoValidationErrorTests(TestCase):
    """Test the Django validation error handler."""

    def test_handle_django_validation_error_with_message_dict(self):
        """Test handling Django ValidationError with field-specific errors."""
        error = DjangoValidationError({"username": ["This field is required."]})
        response = handle_django_validation_error(error)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"username": ["This field is required."]})

    def test_handle_django_validation_error_with_message(self):
        """Test handling Django ValidationError with general message."""
        error = DjangoValidationError("General validation error.")
        response = handle_django_validation_error(error)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "General validation error.")


class ErrorHandlingIntegrationTests(APITestCase):
    """Integration tests for error handling in API views."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            slug="test-campaign",
            owner=self.owner,
            game_system="generic",
        )

    def test_invitation_not_found_security(self):
        """Test that invitation endpoints return 404 for security."""
        self.client.force_authenticate(user=self.user)

        # Test accept invitation with non-existent ID
        response = self.client.post("/api/campaigns/invitations/99999/accept/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

        # Test decline invitation with non-existent ID
        response = self.client.post("/api/campaigns/invitations/99999/decline/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

        # Test cancel invitation with non-existent ID
        response = self.client.delete("/api/campaigns/invitations/99999/cancel/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

    def test_invitation_permission_security(self):
        """Test that invitation endpoints hide existence for unauthorized users."""
        # Create an invitation for another user
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="testpass123"
        )
        invitation = CampaignInvitation.objects.create(
            campaign=self.campaign,
            invited_user=other_user,
            invited_by=self.owner,
            role="PLAYER",
        )

        # Try to access it with wrong user - should return 404 for security
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"/api/campaigns/invitations/{invitation.id}/accept/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")

        response = self.client.post(
            f"/api/campaigns/invitations/{invitation.id}/decline/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Resource not found.")
