"""
User profile API serializers for comprehensive profile management.

These serializers handle API requests/responses for user profile data,
privacy settings, and public profile viewing with proper security controls.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile management API endpoints.

    Provides comprehensive profile data including privacy settings,
    social links, and profile information for authenticated users.
    """

    display_name = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=500)
    avatar = serializers.ImageField(required=False, allow_null=True)
    website_url = serializers.URLField(required=False, allow_blank=True)
    social_links = serializers.JSONField(required=False, default=dict)

    # Privacy settings
    profile_visibility = serializers.ChoiceField(
        choices=[
            ("public", "Public - Visible to everyone"),
            ("members", "Campaign Members - Visible to users in your campaigns"),
            ("private", "Private - Only visible to you"),
        ],
        required=False,
        default="members",
    )
    show_email = serializers.BooleanField(required=False, default=False)
    show_real_name = serializers.BooleanField(required=False, default=True)
    show_last_login = serializers.BooleanField(required=False, default=False)
    allow_activity_tracking = serializers.BooleanField(required=False, default=True)

    # Read-only computed fields
    avatar_url = serializers.SerializerMethodField()
    full_display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "bio",
            "avatar",
            "avatar_url",
            "website_url",
            "social_links",
            "profile_visibility",
            "show_email",
            "show_real_name",
            "show_last_login",
            "allow_activity_tracking",
            "full_display_name",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "last_login",
            "avatar_url",
            "full_display_name",
        ]

    def get_avatar_url(self, obj):
        """Get avatar URL if avatar exists."""
        return obj.get_avatar_url()

    def get_full_display_name(self, obj):
        """Get privacy-aware full display name."""
        return obj.get_full_display_name()

    def validate_avatar(self, value):
        """Validate avatar file size and type."""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Avatar file size must be less than 5MB."
                )

            # Check file type
            allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
            if (
                hasattr(value, "content_type")
                and value.content_type not in allowed_types
            ):
                raise serializers.ValidationError(
                    "Avatar must be a JPEG, PNG, GIF, or WebP image."
                )

        return value

    def validate_social_links(self, value):
        """Validate social links JSON structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Social links must be a valid JSON object."
            )

        # Validate each social link
        for platform, link_value in value.items():
            if link_value and not isinstance(link_value, str):
                raise serializers.ValidationError(
                    f"Social link for {platform} must be a valid string."
                )

            # Platform-specific validation
            if link_value:
                platform_lower = platform.lower()

                # Discord allows usernames (user#1234)
                if platform_lower == "discord":
                    continue  # Allow any non-empty string for Discord

                # For other platforms, require valid URLs
                if not (
                    link_value.startswith("http://")
                    or link_value.startswith("https://")
                ):
                    raise serializers.ValidationError(
                        f"Social link for {platform} must be a valid HTTP/HTTPS URL."
                    )

        return value

    def validate_display_name(self, value):
        """Validate display name uniqueness."""
        if value:
            # Check for uniqueness excluding current user
            existing_user = (
                User.objects.filter(display_name=value)
                .exclude(id=self.instance.id if self.instance else None)
                .first()
            )
            if existing_user:
                raise serializers.ValidationError("This display name is already taken.")

        return value


class PublicUserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for public user profile viewing.

    Returns only privacy-filtered profile data based on the viewer's
    relationship to the profile owner and privacy settings.
    """

    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    website_url = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    last_login = serializers.SerializerMethodField()
    profile_visible = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "display_name",
            "bio",
            "avatar_url",
            "website_url",
            "social_links",
            "email",
            "first_name",
            "last_name",
            "last_login",
            "date_joined",
            "profile_visible",
        ]
        read_only_fields = ["__all__"]  # All fields are read-only for public view

    def __init__(self, *args, **kwargs):
        """Initialize with viewer context for privacy filtering."""
        self.viewer_user = kwargs.pop("viewer_user", None)
        super().__init__(*args, **kwargs)

    def get_profile_data(self, obj):
        """Get privacy-filtered profile data."""
        if not hasattr(self, "_profile_data"):
            self._profile_data = obj.get_public_profile_data(
                viewer_user=self.viewer_user
            )
        return self._profile_data

    def get_display_name(self, obj):
        """Get privacy-filtered display name."""
        return self.get_profile_data(obj).get("display_name", obj.username)

    def get_avatar_url(self, obj):
        """Get avatar URL if visible."""
        return self.get_profile_data(obj).get("avatar_url")

    def get_bio(self, obj):
        """Get bio if visible."""
        return self.get_profile_data(obj).get("bio", "")

    def get_website_url(self, obj):
        """Get website URL if visible."""
        return self.get_profile_data(obj).get("website_url", "")

    def get_social_links(self, obj):
        """Get social links if visible."""
        return self.get_profile_data(obj).get("social_links", {})

    def get_email(self, obj):
        """Get email if user allows email visibility."""
        return self.get_profile_data(obj).get("email")

    def get_first_name(self, obj):
        """Get first name if user shows real name."""
        return self.get_profile_data(obj).get("first_name")

    def get_last_name(self, obj):
        """Get last name if user shows real name."""
        return self.get_profile_data(obj).get("last_name")

    def get_last_login(self, obj):
        """Get last login if user allows last login visibility."""
        return self.get_profile_data(obj).get("last_login")

    def get_profile_visible(self, obj):
        """Check if profile is visible to viewer."""
        return self.get_profile_data(obj).get("profile_visible", False)


class UserPrivacySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for privacy settings management.

    Focused serializer for users who want to manage privacy
    settings separately from other profile information.
    """

    class Meta:
        model = User
        fields = [
            "profile_visibility",
            "show_email",
            "show_real_name",
            "show_last_login",
            "allow_activity_tracking",
        ]

    profile_visibility = serializers.ChoiceField(
        choices=[
            ("public", "Public - Visible to everyone"),
            ("members", "Campaign Members - Visible to users in your campaigns"),
            ("private", "Private - Only visible to you"),
        ]
    )


class UserBasicInfoSerializer(serializers.ModelSerializer):
    """
    Basic user information serializer for internal API usage.

    Used in nested serializations where only basic user data is needed
    without exposing sensitive profile information.
    """

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "display_name"]
        read_only_fields = ["id", "username", "display_name"]

    def get_display_name(self, obj):
        """Get user's preferred display name."""
        return obj.get_display_name()
