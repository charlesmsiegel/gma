"""
API serializers for the GMA application.
"""

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "timezone",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined")


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "username": {"validators": []},  # Remove default unique validator
            "email": {"validators": []},  # Remove default unique validator
        }

    def validate_email(self, value):
        """Validate email is unique (case-insensitive)."""
        if value and User.objects.filter(email__iexact=value).exists():
            # Generic error to prevent email enumeration
            raise serializers.ValidationError(
                "Registration failed. Please try different information."
            )
        return value

    def validate_username(self, value):
        """Validate username is unique."""
        if value and User.objects.filter(username=value).exists():
            # Generic error to prevent username enumeration
            raise serializers.ValidationError(
                "Registration failed. Please try different information."
            )
        return value

    def validate_password(self, value):
        """Validate password strength requirements."""
        import re

        errors = []

        # Check minimum length (8 characters)
        if len(value) < 8:
            errors.append("Password must be at least 8 characters long.")

        # Check for uppercase letter
        if not re.search(r"[A-Z]", value):
            errors.append("Password must contain at least one uppercase letter.")

        # Check for lowercase letter
        if not re.search(r"[a-z]", value):
            errors.append("Password must contain at least one lowercase letter.")

        # Check for digit
        if not re.search(r"\d", value):
            errors.append("Password must contain at least one number.")

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise serializers.ValidationError(" ".join(errors))

        return value

    def validate(self, attrs):
        """Validate passwords match."""
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")
        return attrs

    def create(self, validated_data):
        """Create a new user."""
        # Remove password_confirm from data
        validated_data.pop("password_confirm")

        # Create user with encrypted password
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate credentials and authenticate user with email/username support."""
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            # Handle email authentication like EmailAuthenticationForm
            # Check if input looks like email and try to get user by email first
            if "@" in username:
                try:
                    # Look up user by email (case-insensitive)
                    User = get_user_model()
                    user_obj = User.objects.get(email__iexact=username)
                    # Use the found user's username for authentication
                    user = authenticate(
                        request=self.context.get("request"),
                        username=user_obj.username,
                        password=password,
                    )
                except User.DoesNotExist:
                    # Fall back to regular username authentication
                    user = authenticate(
                        request=self.context.get("request"),
                        username=username,
                        password=password,
                    )
            else:
                # Input is likely a username, authenticate directly
                user = authenticate(
                    request=self.context.get("request"),
                    username=username,
                    password=password,
                )

            if not user:
                raise serializers.ValidationError("Invalid credentials.")

            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")

            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include username and password.")


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile updates."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "display_name", "timezone", "email")

    def validate_email(self, value):
        """Validate email is unique (excluding current user)."""
        if (
            User.objects.exclude(pk=self.instance.pk if self.instance else None)
            .filter(email=value)
            .exists()
        ):
            raise serializers.ValidationError("A user with this email already exists.")
        return value
