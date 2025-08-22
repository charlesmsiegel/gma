"""
API serializers for the GMA application.
"""

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers

from api.messages import ErrorMessages
from campaigns.models import Campaign, CampaignInvitation, CampaignMembership
from characters.models import Character
from locations.models import Location

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


class CampaignMemberSerializer(serializers.ModelSerializer):
    """Simplified serializer for campaign members list."""

    class Meta:
        model = User
        fields = ("id", "username", "email")


class CampaignSettingsSerializer(serializers.Serializer):
    """Separate serializer for campaign settings."""

    visibility = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_visibility(self, obj):
        """Get visibility setting."""
        return "public" if obj.is_public else "private"

    def get_status(self, obj):
        """Get status setting."""
        return "active" if obj.is_active else "inactive"


class CampaignDetailSerializer(CampaignSerializer):
    """Detailed serializer for Campaign model with memberships and settings."""

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
        """Get simplified member list including owner and memberships."""
        # Build owner data
        owner_data = {
            "id": obj.owner.id,
            "username": obj.owner.username,
            "email": obj.owner.email,
            "role": "OWNER",
        }

        # Build membership data using the serializer
        membership_data = []
        for membership in obj.memberships.select_related("user"):
            member_serializer = CampaignMemberSerializer(membership.user)
            member_info = member_serializer.data
            member_info["role"] = membership.role
            membership_data.append(member_info)

        return [owner_data] + membership_data

    def get_settings(self, obj):
        """Get campaign settings only if user is owner."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        if obj.is_owner(request.user):
            settings_serializer = CampaignSettingsSerializer(obj)
            return settings_serializer.data

        return None

    def to_representation(self, instance):
        """Remove settings field for non-owners."""
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


# Invitation-specific serializers
class InvitationUserSerializer(serializers.ModelSerializer):
    """Lightweight user serializer for invitation responses."""

    class Meta:
        model = User
        fields = ("id", "username", "email")


class InvitationCampaignSerializer(serializers.ModelSerializer):
    """Lightweight campaign serializer for invitation responses."""

    class Meta:
        model = Campaign
        fields = ("id", "name", "game_system")


class CampaignInvitationSerializer(serializers.ModelSerializer):
    """Serializer for CampaignInvitation model with nested relationships."""

    campaign = InvitationCampaignSerializer(read_only=True)
    invited_user = InvitationUserSerializer(read_only=True)
    invited_by = InvitationUserSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = CampaignInvitation
        fields = (
            "id",
            "campaign",
            "invited_user",
            "invited_by",
            "role",
            "status",
            "message",
            "created_at",
            "expires_at",
            "is_expired",
        )
        read_only_fields = (
            "id",
            "campaign",
            "invited_user",
            "invited_by",
            "created_at",
            "expires_at",
            "is_expired",
        )


class InvitationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating campaign invitations (response format)."""

    campaign = InvitationCampaignSerializer(read_only=True)
    invited_user = InvitationUserSerializer(read_only=True)
    invited_by = InvitationUserSerializer(read_only=True)

    class Meta:
        model = CampaignInvitation
        fields = (
            "id",
            "campaign",
            "invited_user",
            "invited_by",
            "role",
            "status",
            "message",
            "created_at",
            "expires_at",
        )
        read_only_fields = (
            "id",
            "campaign",
            "invited_user",
            "invited_by",
            "created_at",
            "expires_at",
        )


# Membership response serializers
class MembershipResponseSerializer(serializers.Serializer):
    """Serializer for membership data in invitation acceptance responses."""

    campaign = InvitationCampaignSerializer(read_only=True)
    role = serializers.CharField(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)


class InvitationAcceptResponseSerializer(serializers.Serializer):
    """Serializer for invitation acceptance response."""

    detail = serializers.CharField(read_only=True)
    membership = MembershipResponseSerializer(read_only=True)


# Member list serializers
class CampaignMemberResponseSerializer(serializers.Serializer):
    """Serializer for campaign member data in member list responses."""

    user = InvitationUserSerializer(read_only=True)
    role = serializers.CharField(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)


# Bulk operation serializers
class BulkAddMemberSuccessSerializer(serializers.Serializer):
    """Serializer for successful bulk add member operations."""

    user_id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)


class BulkOperationErrorSerializer(serializers.Serializer):
    """Serializer for bulk operation errors."""

    user_id = serializers.IntegerField(read_only=True, required=False)
    error = serializers.CharField(read_only=True)


class BulkAddMemberResponseSerializer(serializers.Serializer):
    """Serializer for bulk add member response."""

    added = BulkAddMemberSuccessSerializer(many=True, read_only=True)
    failed = BulkOperationErrorSerializer(many=True, read_only=True)


class BulkRoleChangeSuccessSerializer(serializers.Serializer):
    """Serializer for successful bulk role change operations."""

    user_id = serializers.IntegerField(read_only=True)
    role = serializers.CharField(read_only=True)


class BulkRoleChangeResponseSerializer(serializers.Serializer):
    """Serializer for bulk role change response."""

    updated = BulkRoleChangeSuccessSerializer(many=True, read_only=True)
    errors = BulkOperationErrorSerializer(many=True, read_only=True, required=False)


class BulkRemoveMemberSuccessSerializer(serializers.Serializer):
    """Serializer for successful bulk remove member operations."""

    user_id = serializers.IntegerField(read_only=True)


class BulkRemoveMemberResponseSerializer(serializers.Serializer):
    """Serializer for bulk remove member response."""

    removed = BulkRemoveMemberSuccessSerializer(many=True, read_only=True)
    errors = BulkOperationErrorSerializer(many=True, read_only=True, required=False)


# Character API serializers
class CharacterCampaignSerializer(serializers.ModelSerializer):
    """Lightweight campaign serializer for character responses."""

    class Meta:
        model = Campaign
        fields = ("id", "name", "game_system")


class CharacterUserSerializer(serializers.ModelSerializer):
    """Lightweight user serializer for character responses."""

    class Meta:
        model = User
        fields = ("id", "username", "email")


class CharacterSerializer(serializers.ModelSerializer):
    """Serializer for Character model with nested relationships."""

    campaign = CharacterCampaignSerializer(read_only=True)
    player_owner = CharacterUserSerializer(read_only=True)
    deleted_by = CharacterUserSerializer(read_only=True)
    character_type = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = (
            "id",
            "name",
            "description",
            "game_system",
            "npc",
            "created_at",
            "updated_at",
            "campaign",
            "player_owner",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "character_type",
        )
        read_only_fields = (
            "id",
            "game_system",
            "created_at",
            "updated_at",
            "campaign",
            "player_owner",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "character_type",
        )

    def get_character_type(self, obj):
        """Get the polymorphic character type."""
        return obj.__class__.__name__

    def to_representation(self, instance):
        """Use polymorphic serialization for specific character types."""
        # Get the base representation
        data = super().to_representation(instance)

        # Add type-specific fields based on character type
        from characters.models import MageCharacter, WoDCharacter

        if isinstance(instance, MageCharacter):
            # Add Mage-specific fields
            data.update(
                {
                    "arete": instance.arete,
                    "quintessence": instance.quintessence,
                    "paradox": instance.paradox,
                    "willpower": instance.willpower,  # From WoDCharacter
                }
            )
        elif isinstance(instance, WoDCharacter):
            # Add WoD-specific fields
            data.update(
                {
                    "willpower": instance.willpower,
                }
            )

        return data


class CharacterCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating characters."""

    campaign = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.objects.none(),  # Will be set in view
        write_only=True,
        required=False,  # Not required for updates
    )
    character_type = serializers.CharField(
        write_only=True, required=False, help_text="Character type to create"
    )
    # Polymorphic fields for different character types
    willpower = serializers.IntegerField(required=False, min_value=1, max_value=10)
    arete = serializers.IntegerField(required=False, min_value=1, max_value=10)
    quintessence = serializers.IntegerField(required=False, min_value=0)
    paradox = serializers.IntegerField(required=False, min_value=0)

    def run_validation(self, data):
        """
        Override to handle uniqueness constraint violations and readonly
        field filtering.
        """
        # For updates, remove readonly fields from data before validation
        # This prevents validation errors on readonly fields
        if self.instance:  # This is an update operation
            readonly_fields = [
                "campaign",
                "player_owner",
                "game_system",
                "created_at",
                "updated_at",
            ]
            filtered_data = {k: v for k, v in data.items() if k not in readonly_fields}
        else:
            filtered_data = data

        try:
            return super().run_validation(filtered_data)
        except serializers.ValidationError as exc:
            # Check if this is a uniqueness constraint error from full_clean()
            if hasattr(exc, "detail") and isinstance(exc.detail, dict):
                non_field_errors = exc.detail.get("non_field_errors", [])
                if non_field_errors:
                    for error in non_field_errors:
                        error_str = str(error)
                        if (
                            "fields campaign, name must make a unique set" in error_str
                            or "The fields campaign, name must make a unique set"
                            in error_str
                        ):
                            # Convert to field-specific error
                            field_errors = exc.detail.copy()
                            field_errors.pop("non_field_errors", None)
                            field_errors["name"] = [
                                "A character with this name already exists in "
                                "this campaign."
                            ]
                            raise serializers.ValidationError(field_errors)
            raise

    class Meta:
        model = Character
        fields = (
            "name",
            "description",
            "npc",
            "campaign",
            "character_type",
            "willpower",
            "arete",
            "quintessence",
            "paradox",
        )

    def __init__(self, *args, **kwargs):
        """Initialize with user-accessible campaigns."""
        super().__init__(*args, **kwargs)

        # Set campaign queryset based on user in context
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # User can create characters in campaigns they're a member of
            user_campaigns = Campaign.objects.filter(
                models.Q(owner=request.user) | models.Q(memberships__user=request.user)
            ).distinct()
            self.fields["campaign"].queryset = user_campaigns

    def validate_name(self, value):
        """Validate character name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Character name cannot be empty.")

        if len(value) > 100:
            raise serializers.ValidationError(
                "Character name cannot exceed 100 characters."
            )

        name = value.strip()

        # Check uniqueness for creation or when name changes during update
        if self.context.get("request"):
            # Get campaign for uniqueness check
            if not self.instance:  # Creating new character
                # This will be set by the parent validate method after this
                # field validation runs
                # For now, we can't check uniqueness at field level for creation
                pass
            else:  # Updating existing character
                campaign = self.instance.campaign
                # Check if this name conflicts with another character
                existing_qs = Character.all_objects.filter(campaign=campaign, name=name)
                existing_qs = existing_qs.exclude(pk=self.instance.pk)

                if existing_qs.exists():
                    raise serializers.ValidationError(
                        ErrorMessages.CHARACTER_NAME_EXISTS_IN_CAMPAIGN
                    )

        return name

    def validate(self, data):
        """Validate character data including uniqueness and campaign limits."""
        # For updates, remove readonly fields from validation data
        # This ensures we don't try to validate readonly fields that should be ignored
        if self.instance:  # Updating existing character
            readonly_fields = [
                "campaign",
                "player_owner",
                "game_system",
                "created_at",
                "updated_at",
            ]
            for field in readonly_fields:
                data.pop(field, None)

            campaign = self.instance.campaign
        else:  # Creating new character
            campaign = data.get("campaign")
            if not campaign:
                raise serializers.ValidationError(
                    {"campaign": ["Campaign is required."]}
                )

            # Get the user from context
            request = self.context.get("request")
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError(ErrorMessages.UNAUTHORIZED)

            user = request.user

            # Campaign membership is checked in the view's perform_create method

            # Check character limit for the campaign
            if campaign.max_characters_per_player > 0:
                existing_count = Character.objects.filter(
                    campaign=campaign, player_owner=user
                ).count()

                if existing_count >= campaign.max_characters_per_player:
                    char_count = campaign.max_characters_per_player
                    raise serializers.ValidationError(
                        {
                            "campaign": [
                                f"You cannot have more than {char_count} "
                                f"character{'s' if char_count != 1 else ''} in this "
                                f"campaign."
                            ]
                        }
                    )

        # Check character name uniqueness within campaign - this is critical validation
        name = data.get("name", "").strip()
        if name and campaign:
            # Use all_objects to include soft-deleted characters in uniqueness check
            existing_qs = Character.all_objects.filter(campaign=campaign, name=name)
            if self.instance:
                existing_qs = existing_qs.exclude(pk=self.instance.pk)

            if existing_qs.exists():
                # This should prevent the model constraint validation from running
                raise serializers.ValidationError(
                    {
                        "name": [
                            "A character with this name already exists in this "
                            "campaign."
                        ]
                    }
                )

        return data

    def create(self, validated_data):
        """Create character with proper owner and game system."""
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError

        request = self.context.get("request")
        campaign = validated_data["campaign"]

        # Step 1: Prepare data
        prepared_data = self._prepare_character_data(validated_data, request, campaign)

        # Step 2: Create character
        try:
            character = self._create_character_instance(prepared_data)
            character.save(audit_user=request.user)
            return character
        except (IntegrityError, ValidationError) as e:
            raise self._handle_creation_error(e)

    def _prepare_character_data(self, validated_data, request, campaign):
        """Extract and prepare character data for creation."""
        # Set player_owner and game_system
        validated_data["player_owner"] = request.user
        validated_data["game_system"] = campaign.game_system

        # Extract character type and polymorphic fields
        character_type = validated_data.pop("character_type", "Character")
        polymorphic_fields = self._extract_polymorphic_fields(
            validated_data, character_type
        )

        return {
            "base_data": validated_data,
            "character_type": character_type,
            "polymorphic_fields": polymorphic_fields,
        }

    def _extract_polymorphic_fields(self, validated_data, character_type):
        """Extract type-specific fields based on character type."""
        polymorphic_fields = {}

        if character_type == "MageCharacter":
            fields_to_extract = ["willpower", "arete", "quintessence", "paradox"]
        elif character_type == "WoDCharacter":
            fields_to_extract = ["willpower"]
        else:
            fields_to_extract = []

        for field in fields_to_extract:
            if field in validated_data:
                polymorphic_fields[field] = validated_data.pop(field)

        return polymorphic_fields

    def _create_character_instance(self, prepared_data):
        """Create the appropriate character model instance."""
        from characters.models import MageCharacter, WoDCharacter

        character_type = prepared_data["character_type"]
        base_data = prepared_data["base_data"]
        polymorphic_fields = prepared_data["polymorphic_fields"]

        if character_type == "MageCharacter":
            return MageCharacter(**base_data, **polymorphic_fields)
        elif character_type == "WoDCharacter":
            return WoDCharacter(**base_data, **polymorphic_fields)
        else:
            return Character(**base_data)

    def _handle_creation_error(self, error):
        """Handle and transform creation errors into appropriate validation errors."""
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError

        if isinstance(error, IntegrityError):
            return self._handle_integrity_error(error)
        elif isinstance(error, ValidationError):
            return self._handle_validation_error(error)
        else:
            raise error

    def _handle_integrity_error(self, error):
        """Handle database integrity constraint violations."""
        error_message = str(error)
        if self._is_name_uniqueness_error(error_message):
            raise serializers.ValidationError(
                {"name": [ErrorMessages.CHARACTER_NAME_EXISTS_IN_CAMPAIGN]}
            )
        raise error

    def _handle_validation_error(self, error):
        """Handle Django model validation errors."""
        if hasattr(error, "error_dict"):
            return self._handle_error_dict(error.error_dict)

        # Handle single error messages
        if hasattr(error, "message"):
            error_msg = str(error.message)
            if self._is_name_uniqueness_message(error_msg):
                raise serializers.ValidationError(
                    {"name": [ErrorMessages.CHARACTER_NAME_EXISTS_IN_CAMPAIGN]}
                )

        # Handle error message lists
        error_messages = getattr(error, "messages", [getattr(error, "message", None)])
        for msg in error_messages:
            if msg and self._is_name_uniqueness_message(str(msg)):
                raise serializers.ValidationError(
                    {"name": [ErrorMessages.CHARACTER_NAME_EXISTS_IN_CAMPAIGN]}
                )

        # Re-raise the original error if we can't handle it
        raise error

    def _handle_error_dict(self, error_dict):
        """Handle error dictionaries from Django validation errors."""
        # Check for name-specific errors first
        if "name" in error_dict:
            raise serializers.ValidationError(
                {"name": [str(error) for error in error_dict["name"]]}
            )

        # Check for constraint violations in non_field_errors
        if "__all__" in error_dict:
            for error in error_dict["__all__"]:
                error_msg = str(error)
                if self._is_name_uniqueness_message(error_msg):
                    raise serializers.ValidationError(
                        {"name": [ErrorMessages.CHARACTER_NAME_EXISTS_IN_CAMPAIGN]}
                    )

    def _is_name_uniqueness_error(self, error_message):
        """Check if error message indicates a name uniqueness constraint violation."""
        error_lower = error_message.lower()
        return (
            "unique_character_name_per_campaign" in error_message
            or "duplicate key value violates unique constraint" in error_lower
            or ("campaign_id" in error_lower and "name" in error_lower)
        )

    def _is_name_uniqueness_message(self, error_msg):
        """Check if error message indicates name uniqueness violation."""
        return (
            ("Campaign and Name" in error_msg and "unique" in error_msg.lower())
            or "fields campaign, name must make a unique set" in error_msg
            or "campaign, name must make a unique set" in error_msg
            or "The fields campaign, name must make a unique set" in error_msg
        )

    def update(self, instance, validated_data):
        """Update character with audit trail."""
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError

        request = self.context.get("request")

        # Remove campaign from validated_data if present (shouldn't be changed)
        validated_data.pop("campaign", None)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Save with audit user
        try:
            # Skip model validation since serializer validation already handled it
            instance.save(audit_user=request.user, validate=False)
            return instance
        except IntegrityError as e:
            error_message = str(e)
            if "unique_character_name_per_campaign" in error_message:
                raise serializers.ValidationError(
                    {
                        "name": [
                            "A character with this name already exists in this "
                            "campaign."
                        ]
                    }
                )
            raise
        except ValidationError as e:
            # Handle Django model validation errors
            if hasattr(e, "error_dict"):
                # Check for name-specific errors first
                if "name" in e.error_dict:
                    raise serializers.ValidationError(
                        {"name": [str(error) for error in e.error_dict["name"]]}
                    )
                # Check for constraint violations in non_field_errors
                elif "__all__" in e.error_dict:
                    for error in e.error_dict["__all__"]:
                        error_msg = str(error)
                        if (
                            (
                                "Campaign and Name" in error_msg
                                and "unique" in error_msg.lower()
                            )
                            or (
                                "fields campaign, name must make a unique set"
                                in error_msg
                            )
                            or ("campaign, name must make a unique set" in error_msg)
                            or (
                                "The fields campaign, name must make a unique set"
                                in error_msg
                            )
                        ):
                            raise serializers.ValidationError(
                                {
                                    "name": [
                                        "A character with this name already exists "
                                        "in this campaign."
                                    ]
                                }
                            )
            # Check for single error messages as well
            if hasattr(e, "message"):
                error_msg = str(e.message)
                if "Campaign and Name" in error_msg and "unique" in error_msg.lower():
                    raise serializers.ValidationError(
                        {
                            "name": [
                                "A character with this name already exists "
                                "in this campaign."
                            ]
                        }
                    )
            # Re-raise the original error if we can't handle it
            raise

    def to_representation(self, instance):
        """Return full character representation."""
        # Use the main CharacterSerializer for response
        serializer = CharacterSerializer(instance, context=self.context)
        return serializer.data


# Location API serializers
class LocationCampaignSerializer(serializers.ModelSerializer):
    """Lightweight campaign serializer for location responses."""

    class Meta:
        model = Campaign
        fields = ("id", "name")


class LocationCharacterSerializer(serializers.ModelSerializer):
    """Lightweight character serializer for location owner responses."""

    class Meta:
        model = Character
        fields = ("id", "name", "npc")


class LocationCreatedBySerializer(serializers.ModelSerializer):
    """Lightweight user serializer for location creator responses."""

    class Meta:
        model = User
        fields = ("id", "username")


class LocationParentSerializer(serializers.ModelSerializer):
    """Serializer for parent location reference."""

    class Meta:
        model = Location
        fields = ("id", "name")


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model with hierarchy and ownership info."""

    campaign = LocationCampaignSerializer(read_only=True)
    owned_by = LocationCharacterSerializer(read_only=True)
    created_by = LocationCreatedBySerializer(read_only=True)
    parent = LocationParentSerializer(read_only=True)
    children_count = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField()
    hierarchy_path = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()
    siblings_count = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            "id",
            "name",
            "description",
            "campaign",
            "parent",
            "owned_by",
            "created_by",
            "created_at",
            "updated_at",
            "children_count",
            "depth",
            "hierarchy_path",
            "ancestors",
            "siblings_count",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "children_count",
            "depth",
            "hierarchy_path",
            "ancestors",
            "siblings_count",
        )

    def get_children_count(self, obj):
        """Get the number of child locations."""
        return obj.children.count()

    def get_depth(self, obj):
        """Get the depth of this location in the hierarchy."""
        return obj.get_depth()

    def get_hierarchy_path(self, obj):
        """Get the full path from root to this location."""
        return obj.get_full_path()

    def get_ancestors(self, obj):
        """Get the ancestors of this location."""
        ancestors = obj.get_ancestors()
        return LocationParentSerializer(ancestors, many=True).data

    def get_siblings_count(self, obj):
        """Get the number of sibling locations."""
        return obj.get_siblings().count()


class LocationDetailSerializer(LocationSerializer):
    """Detailed serializer for Location with children and additional info."""

    children = LocationSerializer(many=True, read_only=True)
    siblings = serializers.SerializerMethodField()

    class Meta(LocationSerializer.Meta):
        fields = LocationSerializer.Meta.fields + ("children", "siblings")

    def get_siblings(self, obj):
        """Get siblings of this location."""
        siblings = obj.get_siblings()
        return LocationSerializer(siblings, many=True, context=self.context).data


class LocationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating locations."""

    campaign = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.objects.none(),  # Will be set in view
        write_only=True,
        required=False,  # Not required for updates
    )
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.none(),  # Will be set in view
        required=False,
        allow_null=True,
    )
    owned_by = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.none(),  # Will be set in view
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Location
        fields = (
            "name",
            "description",
            "campaign",
            "parent",
            "owned_by",
        )

    def __init__(self, *args, **kwargs):
        """Initialize with user-accessible campaigns and related objects."""
        super().__init__(*args, **kwargs)

        # Set querysets based on user in context
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # User can create locations in campaigns they're a member of
            user_campaigns = Campaign.objects.filter(
                models.Q(owner=request.user) | models.Q(memberships__user=request.user)
            ).distinct()
            self.fields["campaign"].queryset = user_campaigns

            # If we have a campaign context, limit parent and character choices
            campaign_id = self.context.get("campaign_id")
            if campaign_id:
                campaign = Campaign.objects.filter(id=campaign_id).first()
                if campaign:
                    # Parent must be in same campaign
                    self.fields["parent"].queryset = Location.objects.filter(
                        campaign=campaign
                    )
                    # Character owner must be in same campaign
                    self.fields["owned_by"].queryset = Character.objects.filter(
                        campaign=campaign
                    )
            else:
                # For updates, use the instance's campaign
                if self.instance:
                    campaign = self.instance.campaign
                    self.fields["parent"].queryset = Location.objects.filter(
                        campaign=campaign
                    ).exclude(
                        pk=self.instance.pk
                    )  # Exclude self
                    self.fields["owned_by"].queryset = Character.objects.filter(
                        campaign=campaign
                    )

    def validate_name(self, value):
        """Validate location name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Location name cannot be empty.")

        if len(value) > 200:  # Assuming max length from model
            raise serializers.ValidationError(
                "Location name cannot exceed 200 characters."
            )

        return value.strip()

    def validate(self, data):
        """Validate location data including hierarchy constraints."""
        # For updates, handle campaign context differently
        if self.instance:  # Updating existing location
            campaign = self.instance.campaign
            # Remove campaign from data if present (shouldn't be changed)
            data.pop("campaign", None)
        else:  # Creating new location
            campaign = data.get("campaign")
            if not campaign:
                raise serializers.ValidationError(
                    {"campaign": ["Campaign is required."]}
                )

            # Check if user can create locations in this campaign
            request = self.context.get("request")
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError(ErrorMessages.UNAUTHORIZED)

            user = request.user
            if not Location.can_create(user, campaign):
                raise serializers.ValidationError(
                    {
                        "campaign": [
                            "You don't have permission to create locations "
                            "in this campaign."
                        ]
                    }
                )

        # Validate parent location
        parent = data.get("parent")
        if parent:
            # Ensure parent is in the same campaign
            if parent.campaign != campaign:
                raise serializers.ValidationError(
                    {"parent": ["Parent location must be in the same campaign."]}
                )

            # For updates, prevent circular references
            if self.instance and (
                parent == self.instance or self.instance.is_descendant_of(parent)
            ):
                raise serializers.ValidationError(
                    {
                        "parent": [
                            "Circular reference detected: this location cannot "
                            "be a parent of its ancestor or descendant."
                        ]
                    }
                )

            # Check maximum depth
            future_depth = parent.get_depth() + 1
            if future_depth >= 10:  # Maximum depth of 10 levels
                raise serializers.ValidationError(
                    {
                        "parent": [
                            f"Maximum depth of 10 levels exceeded. "
                            f"This location would be at depth {future_depth}."
                        ]
                    }
                )

        # Validate character ownership
        owned_by = data.get("owned_by")
        if owned_by and owned_by.campaign != campaign:
            raise serializers.ValidationError(
                {
                    "owned_by": [
                        "Location owner must be a character in the same campaign."
                    ]
                }
            )

        return data

    def create(self, validated_data):
        """Create location with proper audit user."""
        request = self.context.get("request")
        location = Location(**validated_data)
        location.save(user=request.user)
        return location

    def update(self, instance, validated_data):
        """Update location with audit trail."""
        request = self.context.get("request")

        # Remove campaign from validated_data if present (shouldn't be changed)
        validated_data.pop("campaign", None)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Save with audit user
        instance.save(user=request.user)
        return instance

    def to_representation(self, instance):
        """Return full location representation."""
        # Use the main LocationSerializer for response
        serializer = LocationSerializer(instance, context=self.context)
        return serializer.data


# Bulk operation serializers for locations
class BulkLocationCreateSerializer(serializers.Serializer):
    """Serializer for bulk location creation data."""

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    campaign = serializers.PrimaryKeyRelatedField(queryset=Campaign.objects.all())
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False, allow_null=True
    )
    parent_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Reference parent by name within the same batch",
    )
    owned_by = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(), required=False, allow_null=True
    )


class BulkLocationUpdateSerializer(serializers.Serializer):
    """Serializer for bulk location update data."""

    id = serializers.IntegerField()
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False, allow_null=True
    )
    owned_by = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(), required=False, allow_null=True
    )


class BulkLocationDeleteSerializer(serializers.Serializer):
    """Serializer for bulk location deletion data."""

    id = serializers.IntegerField()


class BulkLocationMoveSerializer(serializers.Serializer):
    """Serializer for bulk location move data."""

    id = serializers.IntegerField()
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False, allow_null=True
    )


class BulkLocationOperationSerializer(serializers.Serializer):
    """Serializer for bulk location operations."""

    action = serializers.ChoiceField(
        choices=["create", "update", "delete", "move"],
        help_text="The type of bulk operation to perform",
    )
    locations = serializers.JSONField(
        help_text="Array of location data based on the action type"
    )

    def validate(self, data):
        """Validate bulk operation data."""
        action = data.get("action")
        locations = data.get("locations", [])

        if not locations:
            raise serializers.ValidationError(
                {"locations": ["At least one location must be provided."]}
            )

        if len(locations) > 100:  # Reasonable limit for bulk operations
            raise serializers.ValidationError(
                {"locations": ["Cannot process more than 100 locations at once."]}
            )

        # Validate each location item based on action
        validated_locations = []
        for i, location_data in enumerate(locations):
            try:
                if action == "create":
                    serializer = BulkLocationCreateSerializer(data=location_data)
                elif action == "update":
                    serializer = BulkLocationUpdateSerializer(data=location_data)
                elif action == "delete":
                    serializer = BulkLocationDeleteSerializer(data=location_data)
                elif action == "move":
                    serializer = BulkLocationMoveSerializer(data=location_data)

                if serializer.is_valid(raise_exception=True):
                    validated_locations.append(serializer.validated_data)
            except serializers.ValidationError as e:
                raise serializers.ValidationError(
                    {"locations": [f"Item {i}: {e.detail}"]}
                )

        data["locations"] = validated_locations
        return data


class BulkLocationSuccessSerializer(serializers.Serializer):
    """Serializer for successful bulk location operations."""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    action = serializers.CharField(read_only=True)


class BulkLocationErrorSerializer(serializers.Serializer):
    """Serializer for bulk location operation errors."""

    item_index = serializers.IntegerField(read_only=True, required=False)
    name = serializers.CharField(read_only=True, required=False)
    error = serializers.CharField(read_only=True)


class BulkLocationResponseSerializer(serializers.Serializer):
    """Serializer for bulk location operation response."""

    created = LocationSerializer(many=True, read_only=True, required=False)
    updated = LocationSerializer(many=True, read_only=True, required=False)
    deleted = BulkLocationSuccessSerializer(many=True, read_only=True, required=False)
    moved = LocationSerializer(many=True, read_only=True, required=False)
    failed = BulkLocationErrorSerializer(many=True, read_only=True, required=False)
