"""
Integration tests for API authentication endpoints.

These tests verify end-to-end authentication workflows that mirror
how Django templates with JavaScript interact with Django API endpoints,
including session management, CSRF handling, and error responses.
"""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class AuthenticationIntegrationTest(TestCase):
    """Test complete authentication workflows as used by Django templates."""

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

    def test_complete_login_workflow_with_csrf(self):
        """Test complete login workflow including CSRF token handling."""
        # Step 1: Get CSRF token (as JavaScript in templates would)
        csrf_response = self.client.get(self.csrf_url)
        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", csrf_response.data)
        csrf_token = csrf_response.data["csrfToken"]

        # Step 2: Login with CSRF token in headers (as fetch API would send)
        login_data = {"username": "testuser", "password": "TestPass123!"}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["message"], "Login successful")
        self.assertIn("user", login_response.data)
        self.assertEqual(login_response.data["user"]["username"], "testuser")
        self.assertEqual(login_response.data["user"]["email"], "test@example.com")

        # Step 3: Verify session is established by accessing user info
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_info_response.data["user"]["username"], "testuser")

    def test_complete_email_login_workflow(self):
        """Test complete login workflow using email instead of username."""
        # Get CSRF token
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Login with email (case-insensitive)
        login_data = {"username": "TEST@EXAMPLE.COM", "password": "TestPass123!"}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["message"], "Login successful")
        self.assertEqual(login_response.data["user"]["username"], "testuser")

        # Verify session works
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_200_OK)

    def test_complete_registration_workflow(self):
        """Test complete registration workflow including immediate login."""
        # Get CSRF token
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Register new user
        registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        register_response = self.client.post(
            self.register_url,
            data=json.dumps(registration_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            register_response.data["message"], "User registered successfully"
        )
        self.assertIn("user", register_response.data)
        self.assertEqual(register_response.data["user"]["username"], "newuser")

        # Verify user was created in database
        self.assertTrue(User.objects.filter(username="newuser").exists())
        new_user = User.objects.get(username="newuser")
        self.assertEqual(new_user.email, "newuser@example.com")
        self.assertEqual(new_user.first_name, "New")
        self.assertEqual(new_user.last_name, "User")

        # Step 2: Login with the new user credentials
        login_data = {"username": "newuser", "password": "NewPass123!"}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Step 3: Verify the user can access protected endpoints
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_200_OK)
        self.assertEqual(user_info_response.data["user"]["username"], "newuser")

    def test_complete_logout_workflow(self):
        """Test complete logout workflow and session cleanup."""
        # First login
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        login_data = {"username": "testuser", "password": "TestPass123!"}
        self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        # Verify we're logged in
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_200_OK)

        # Logout
        logout_response = self.client.post(
            self.logout_url,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(logout_response.data["message"], "Logout successful")

        # Verify we can't access protected endpoints after logout
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_persistence_across_requests(self):
        """Test that sessions persist across multiple API requests."""
        # Login
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        login_data = {"username": "testuser", "password": "TestPass123!"}
        self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        # Make multiple requests to verify session persists
        for _ in range(3):
            user_info_response = self.client.get(self.user_info_url)
            self.assertEqual(user_info_response.status_code, status.HTTP_200_OK)
            self.assertEqual(user_info_response.data["user"]["username"], "testuser")

    def test_authentication_error_responses_for_javascript(self):
        """Test that error responses are properly formatted for JavaScript."""
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        # Test invalid login credentials
        login_data = {"username": "testuser", "password": "WrongPassword"}
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", login_response.data)
        self.assertEqual(
            login_response.data["non_field_errors"], ["Invalid credentials."]
        )

        # Test missing required fields
        incomplete_login_data = {"username": "testuser"}
        incomplete_login_response = self.client.post(
            self.login_url,
            data=json.dumps(incomplete_login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(
            incomplete_login_response.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertIn("password", incomplete_login_response.data)

        # Test registration validation errors
        invalid_registration_data = {
            "username": "testuser",  # Already exists
            "email": "test@example.com",  # Already exists
            "password": "weak",  # Too weak
            "password_confirm": "different",  # Doesn't match
        }
        register_response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_registration_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(register_response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that proper field-level errors are returned for JavaScript handling
        self.assertTrue(
            "username" in register_response.data
            or "email" in register_response.data
            or "password" in register_response.data
            or "non_field_errors" in register_response.data
        )

    def test_csrf_protection_enforcement(self):
        """
        Test that CSRF protection is properly enforced for state-changing operations.
        """
        from django.test.client import Client

        # Use regular Django client to test CSRF protection more realistically
        regular_client = Client(enforce_csrf_checks=True)

        # Get CSRF token first
        csrf_response = regular_client.get(self.csrf_url)
        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        csrf_token = csrf_response.json()["csrfToken"]

        # Test 1: Valid request with proper CSRF token should work
        login_data = {"username": "testuser", "password": "TestPass123!"}
        valid_login_response = regular_client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(valid_login_response.status_code, status.HTTP_200_OK)

        # Logout for clean state
        regular_client.post(
            self.logout_url,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        # Test 2: Request with invalid CSRF token should fail
        invalid_login_response = regular_client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN="invalid-token",
        )
        self.assertEqual(
            invalid_login_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # Test 3: Request without CSRF token should fail
        no_csrf_login_response = regular_client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            # No CSRF token provided
        )
        self.assertEqual(no_csrf_login_response.status_code, status.HTTP_403_FORBIDDEN)

        # Test 4: Same for registration endpoint
        registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }
        no_csrf_register_response = regular_client.post(
            self.register_url,
            data=json.dumps(registration_data),
            content_type="application/json",
            # No CSRF token provided
        )
        self.assertEqual(
            no_csrf_register_response.status_code, status.HTTP_403_FORBIDDEN
        )

    def test_unauthenticated_access_to_protected_endpoints(self):
        """Test that protected endpoints properly reject unauthenticated requests."""
        # User info endpoint should require authentication
        user_info_response = self.client.get(self.user_info_url)
        self.assertEqual(user_info_response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Logout endpoint should require authentication
        csrf_response = self.client.get(self.csrf_url)
        csrf_token = csrf_response.data["csrfToken"]

        logout_response = self.client.post(
            self.logout_url,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(logout_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_concurrent_session_handling(self):
        """Test that the system handles concurrent sessions properly."""
        # Create two separate clients to simulate different browser sessions
        client1 = APIClient()
        client2 = APIClient()

        # Both get CSRF tokens
        csrf_response1 = client1.get(self.csrf_url)
        csrf_token1 = csrf_response1.data["csrfToken"]

        csrf_response2 = client2.get(self.csrf_url)
        csrf_token2 = csrf_response2.data["csrfToken"]

        # Both login with the same user
        login_data = {"username": "testuser", "password": "TestPass123!"}

        login_response1 = client1.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token1,
        )
        self.assertEqual(login_response1.status_code, status.HTTP_200_OK)

        login_response2 = client2.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token2,
        )
        self.assertEqual(login_response2.status_code, status.HTTP_200_OK)

        # Both should be able to access user info
        user_info_response1 = client1.get(self.user_info_url)
        self.assertEqual(user_info_response1.status_code, status.HTTP_200_OK)

        user_info_response2 = client2.get(self.user_info_url)
        self.assertEqual(user_info_response2.status_code, status.HTTP_200_OK)

        # Logout from one session shouldn't affect the other
        logout_response1 = client1.post(
            self.logout_url,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token1,
        )
        self.assertEqual(logout_response1.status_code, status.HTTP_200_OK)

        # Client1 should be logged out
        user_info_response1 = client1.get(self.user_info_url)
        self.assertEqual(user_info_response1.status_code, status.HTTP_401_UNAUTHORIZED)

        # Client2 should still be logged in
        user_info_response2 = client2.get(self.user_info_url)
        self.assertEqual(user_info_response2.status_code, status.HTTP_200_OK)
