"""
API serializers for the GMA application.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from campaigns.models import Campaign, CampaignMembership

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
        """Validate password using Django's built-in password validators."""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

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
        from users.utils import authenticate_by_email_or_username

        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate_by_email_or_username(
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


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model."""

    owner = UserSerializer(read_only=True)

    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "game_system",
            "is_active",
            "created_at",
            "updated_at",
            "owner",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at", "owner")

    def validate_name(self, value):
        """Validate campaign name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Campaign name is required.")

        # Trim whitespace
        value = value.strip()

        if len(value) > 200:
            raise serializers.ValidationError(
                "Campaign name must not exceed 200 characters."
            )

        return value

    def validate_description(self, value):
        """Clean description field."""
        return value.strip() if value else ""

    def validate_game_system(self, value):
        """Clean game system field."""
        return value.strip() if value else ""

    def create(self, validated_data):
        """Create campaign with owner from request."""
        # Owner should be passed via save(owner=user) in the view
        return super().create(validated_data)


class CampaignMembershipSerializer(serializers.ModelSerializer):
    """Serializer for CampaignMembership model."""

    user = UserSerializer(read_only=True)
    campaign = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CampaignMembership
        fields = (
            "id",
            "campaign",
            "user",
            "role",
            "joined_at",
        )
        read_only_fields = ("id", "campaign", "user", "joined_at")


class CampaignDetailSerializer(CampaignSerializer):
    """Detailed serializer for Campaign model with memberships."""

    memberships = CampaignMembershipSerializer(many=True, read_only=True)

    class Meta(CampaignSerializer.Meta):
        fields = CampaignSerializer.Meta.fields + ("memberships",)
