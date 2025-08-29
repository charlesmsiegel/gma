"""
Tests that verify API response patterns match Django template integration.

These tests ensure that the API responses are structured in a way that
Django templates and JavaScript can properly handle, including error messages,
data structures, and HTTP status codes for AJAX requests.
"""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class FrontendIntegrationPatternsTest(TestCase):
    """Test that API responses match Django template JavaScript expectations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            display_name="TestUser",
        )

        # API endpoints
        self.csrf_url = reverse("api:auth:api_csrf_token")
        self.login_url = reverse("api:auth:api_login")
        self.register_url = reverse("api:auth:api_register")
        self.logout_url = reverse("api:auth:api_logout")
        self.user_info_url = reverse("api:auth:api_user_info")

    def test_login_response_structure_for_javascript(self):
        """Test that login response matches JavaScript fetch/ajax expectations."""
        # Get CSRF token
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Successful login
        login_data = {"username": "testuser", "password": "TestPass123!"}
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response structure matches JavaScript expectations
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        # Verify all fields that JavaScript code expects
        expected_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "timezone",
            "date_joined",
        ]
        for field in expected_fields:
            self.assertIn(field, user_data)

    def test_login_error_response_structure_for_javascript(self):
        """Test that login errors match JavaScript error handling expectations."""
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Failed login
        login_data = {"username": "testuser", "password": "WrongPassword"}
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # JavaScript error handling expects error in non_field_errors array format
        # for consistent error display in Django templates
        self.assertIn("non_field_errors", response.data)
        self.assertIsInstance(response.data["non_field_errors"], list)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "Invalid credentials.",
        )

    def test_registration_response_structure_for_javascript(self):
        """
        Test that registration response matches JavaScript registration expectations.
        """
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Successful registration
        registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post(
            self.register_url,
            data=json.dumps(registration_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify response structure matches JavaScript expectations
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(
            response.data["message"],
            "User registered successfully",
        )

    def test_registration_error_response_structure_for_javascript(self):
        """
        Test that registration errors match JavaScript error handling expectations.
        """
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Registration with various validation errors
        invalid_data = {
            "username": "testuser",  # Already exists
            "email": "test@example.com",  # Already exists
            "password": "weak",  # Too weak
            "password_confirm": "different",  # Doesn't match
        }
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # JavaScript registration checks for field-specific errors
        # for displaying validation messages in Django templates
        # At least one of these error types should be present
        has_expected_error = any(
            [
                "username" in response.data,
                "email" in response.data,
                "password" in response.data,
                "detail" in response.data,
                "non_field_errors" in response.data,
            ]
        )
        self.assertTrue(
            has_expected_error,
            f"Response should contain expected error fields: {response.data}",
        )

    def test_user_info_response_structure(self):
        """Test that user info response matches JavaScript/template expectations."""
        # Login first
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        login_data = {"username": "testuser", "password": "TestPass123!"}
        self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        # Get user info
        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)

        # Verify all expected user fields are present
        user_data = response.data["user"]
        expected_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "timezone",
            "date_joined",
        ]
        for field in expected_fields:
            self.assertIn(field, user_data)

    def test_csrf_token_response_structure(self):
        """Test that CSRF token response matches JavaScript fetch expectations."""
        # JavaScript fetch API expects { csrfToken: string } for AJAX requests
        response = self.client.get(self.csrf_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.data)
        self.assertIsInstance(response.data["csrfToken"], str)
        self.assertGreater(len(response.data["csrfToken"]), 0)

    def test_logout_response_structure(self):
        """Test that logout response matches JavaScript expectations."""
        # Login first
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        login_data = {"username": "testuser", "password": "TestPass123!"}
        self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        # Logout
        response = self.client.post(
            self.logout_url,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Logout successful")

    def test_api_content_type_handling(self):
        """Test that API properly handles JSON content type as sent by fetch."""
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # JavaScript fetch API uses 'application/json' content type
        login_data = {"username": "testuser", "password": "TestPass123!"}
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),  # JSON string, not form data
            content_type="application/json",  # fetch API default
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response is also JSON (DRF default)
        self.assertEqual(response.get("Content-Type"), "application/json")

    def test_fetch_credentials_and_session_handling(self):
        """Test that session cookies work with fetch credentials: 'include'."""
        # This tests the Django side of session handling
        # fetch sends credentials: 'include', Django should set/read session cookies

        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Login
        login_data = {"username": "testuser", "password": "TestPass123!"}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Verify session cookie is set (Django test client automatically handles this)
        # In a real browser, this would be the Set-Cookie header with sessionid
        self.assertTrue(self.client.session.session_key)

        # Subsequent request should maintain session without re-authentication
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_200_OK)

    def test_error_response_status_codes_for_javascript(self):
        """Test that error status codes match what JavaScript error handlers expect."""
        # JavaScript may have error handlers that handle different status codes

        # 400 for validation errors
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        invalid_login = self.client.post(
            self.login_url,
            data=json.dumps({"username": "invalid", "password": "invalid"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(invalid_login.status_code, 400)

        # 401 for authentication required (unauthenticated user)
        protected_response = self.client.get(self.user_info_url)
        self.assertEqual(protected_response.status_code, 401)

        # Note: CSRF protection testing is covered in test_auth_integration.py
