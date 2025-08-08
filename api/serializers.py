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
    """Serializer for Campaign model with user role and member count."""

    owner = UserSerializer(read_only=True)
    user_role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "game_system",
            "is_active",
            "is_public",
            "created_at",
            "updated_at",
            "owner",
            "user_role",
            "member_count",
        )
        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
            "owner",
            "user_role",
            "member_count",
        )

    def get_user_role(self, obj):
        """Get the current user's role in this campaign."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return obj.get_user_role(request.user)

    def get_member_count(self, obj):
        """Get the total number of members in this campaign."""
        # Count owner + memberships
        return 1 + obj.memberships.count()

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
    """Detailed serializer for Campaign model with memberships and role-specific data."""  # noqa: E501

    memberships = CampaignMembershipSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()

    class Meta(CampaignSerializer.Meta):
        fields = CampaignSerializer.Meta.fields + (
            "memberships",
            "members",
            "settings",
        )

    def get_members(self, obj):
        """Get member list - always include for detail view."""
        members_data = []

        # Add owner
        members_data.append(
            {
                "id": obj.owner.id,
                "username": obj.owner.username,
                "email": obj.owner.email,
                "role": "OWNER",
            }
        )

        # Add other members
        for membership in obj.memberships.all():
            members_data.append(
                {
                    "id": membership.user.id,
                    "username": membership.user.username,
                    "email": membership.user.email,
                    "role": membership.role,
                }
            )

        return members_data

    def get_settings(self, obj):
        """Get campaign settings - only for owners."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        if obj.is_owner(request.user):
            return {
                "visibility": "public" if obj.is_public else "private",
                "status": "active" if obj.is_active else "inactive",
            }
        return None

    def to_representation(self, instance):
        """Customize representation to conditionally include settings field."""
        data = super().to_representation(instance)

        # Remove settings field if user is not owner
        request = self.context.get("request")
        if (
            not request
            or not request.user.is_authenticated
            or not instance.is_owner(request.user)
        ):
            data.pop("settings", None)

        return data
