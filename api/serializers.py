"""
API serializers for the GMA application.
"""

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers

from api.messages import ErrorMessages
from campaigns.models import Campaign, CampaignInvitation, CampaignMembership
from characters.models import Character
from items.models import Item
from locations.models import Location
from scenes.models import Message, Scene
from users.models.password_reset import PasswordReset
from users.models.session_models import SessionSecurityLog, UserSession

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
            "email_verified",
        )
        read_only_fields = ("id", "date_joined", "email_verified")


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
            "display_name",
        )
        extra_kwargs = {
            "username": {"validators": []},  # Remove default unique validator
            "email": {"validators": []},  # Remove default unique validator
        }

    def validate_email(self, value):
        """Validate email format and uniqueness (case-insensitive)."""
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email

        if not value:
            raise serializers.ValidationError("Email is required.")

        # Validate email format
        try:
            validate_email(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid email address.")

        # Check for very long emails
        if len(value) > 254:  # RFC 5321 limit
            raise serializers.ValidationError("Email address is too long.")

        # Check uniqueness
        if User.objects.filter(email__iexact=value).exists():
            # Generic error to prevent email enumeration
            raise serializers.ValidationError(
                "Registration failed. Please try different information."
            )
        return value

    def validate_username(self, value):
        """Validate username format and uniqueness."""
        if not value:
            raise serializers.ValidationError("Username is required.")

        # Basic format validation
        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must be at least 3 characters long."
            )

        if len(value) > 150:  # Django User model default max_length
            raise serializers.ValidationError("Username is too long.")

        # Check uniqueness
        if User.objects.filter(username=value).exists():
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
        """Create a new user with email verification."""
        from django.db import transaction

        from users.models import EmailVerification
        from users.services import EmailVerificationService

        # Remove password_confirm from data
        validated_data.pop("password_confirm")

        with transaction.atomic():
            # Create user with encrypted password
            user = User.objects.create_user(**validated_data)

            # Set email as unverified
            user.email_verified = False

            # Handle display_name
            display_name = validated_data.get("display_name")
            if display_name:
                user.display_name = display_name
            else:
                user.display_name = None  # For unique constraint

            user.save()

            # Create email verification record
            verification = EmailVerification.create_for_user(user)

            # Update user's verification fields
            user.email_verification_token = verification.token
            user.email_verification_sent_at = verification.created_at
            user.save(
                update_fields=["email_verification_token", "email_verification_sent_at"]
            )

            # Send verification email
            service = EmailVerificationService()
            try:
                service.send_verification_email(user)
            except Exception:  # nosec B110
                # Don't fail registration if email sending fails - intentional
                pass

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
    """
    Base serializer for Location model with conditional field inclusion.

    Uses database annotations for performance optimization and includes
    fields based on context to avoid circular references.
    """

    campaign = LocationCampaignSerializer(read_only=True)
    owned_by = LocationCharacterSerializer(read_only=True)
    created_by = LocationCreatedBySerializer(read_only=True)
    parent = LocationParentSerializer(read_only=True)

    # Use annotated fields when available, fallback to method fields
    children_count = serializers.IntegerField(read_only=True)
    siblings_count = serializers.IntegerField(read_only=True)
    depth = serializers.SerializerMethodField()
    hierarchy_path = serializers.SerializerMethodField()

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
            "siblings_count",
            "depth",
            "hierarchy_path",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "children_count",
            "siblings_count",
            "depth",
            "hierarchy_path",
        )

    def get_depth(self, obj):
        """Get the depth of this location in the hierarchy."""
        # Use annotated value if available, otherwise compute
        if hasattr(obj, "_depth"):
            return obj._depth
        return obj.get_depth()

    def get_hierarchy_path(self, obj):
        """Get the full hierarchy path for this location."""
        # Build path efficiently without additional queries since parent is
        # select_related
        path_parts = []
        current = obj
        visited = set()  # Prevent infinite loops

        # Traverse up the parent chain using the already-loaded parent relationships
        while current and current.pk not in visited and len(visited) < 50:
            visited.add(current.pk)
            path_parts.append(current.name)
            current = current.parent

        # Reverse to get root-to-current order and join
        path_parts.reverse()
        return " > ".join(path_parts)


class LocationDetailSerializer(LocationSerializer):
    """
    Extended serializer for Location detail views with children and siblings.

    Fixes circular reference by using simple structure for nested objects.
    """

    # Use simple serializers to avoid infinite recursion
    children = serializers.SerializerMethodField()
    siblings = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()

    class Meta(LocationSerializer.Meta):
        fields = LocationSerializer.Meta.fields + ("children", "siblings", "ancestors")

    def get_children(self, obj):
        """Get immediate children with basic info to avoid recursion."""
        children = obj.children.all()
        return [
            {
                "id": child.id,
                "name": child.name,
                "description": child.description,
                "owned_by": (
                    LocationCharacterSerializer(child.owned_by).data
                    if child.owned_by
                    else None
                ),
                "children_count": getattr(
                    child, "children_count", child.children.count()
                ),
            }
            for child in children
        ]

    def get_siblings(self, obj):
        """Get siblings with basic info to avoid recursion."""
        siblings = obj.get_siblings()
        return [
            {
                "id": sibling.id,
                "name": sibling.name,
                "description": sibling.description,
                "children_count": getattr(
                    sibling, "children_count", sibling.children.count()
                ),
            }
            for sibling in siblings
        ]

    def get_ancestors(self, obj):
        """Get ancestor locations ordered from immediate parent to root."""
        ancestors = obj.get_ancestors()
        return [
            {
                "id": ancestor.id,
                "name": ancestor.name,
            }
            for ancestor in ancestors
        ]


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
                parent == self.instance or parent.is_descendant_of(self.instance)
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


# Item API serializers
class ItemCampaignSerializer(serializers.ModelSerializer):
    """Lightweight campaign serializer for item responses."""

    class Meta:
        model = Campaign
        fields = ("id", "name")


class ItemCharacterSerializer(serializers.ModelSerializer):
    """Lightweight character serializer for item owner responses."""

    class Meta:
        model = Character
        fields = ("id", "name", "npc")


class ItemCreatedBySerializer(serializers.ModelSerializer):
    """Lightweight user serializer for item creator responses."""

    class Meta:
        model = User
        fields = ("id", "username")


class ItemSerializer(serializers.ModelSerializer):
    """
    Base serializer for Item model with nested relationships.

    Includes polymorphic_ctype field for future polymorphic subclasses
    and all fields necessary for comprehensive item management.
    """

    campaign = ItemCampaignSerializer(read_only=True)
    owner = ItemCharacterSerializer(read_only=True)
    created_by = ItemCreatedBySerializer(read_only=True)
    deleted_by = ItemCreatedBySerializer(read_only=True)
    polymorphic_ctype = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = (
            "id",
            "name",
            "description",
            "quantity",
            "campaign",
            "owner",
            "created_by",
            "created_at",
            "updated_at",
            "last_transferred_at",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "polymorphic_ctype",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "last_transferred_at",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "polymorphic_ctype",
        )

    def get_polymorphic_ctype(self, obj):
        """Get the polymorphic content type for future subclasses."""
        return {
            "app_label": obj._meta.app_label,
            "model": obj._meta.model_name,
        }


class ItemCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating items."""

    campaign = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.objects.none(),  # Will be set in view
        write_only=True,
        required=False,  # Not required for updates
    )
    owner = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.none(),  # Will be set in view
        required=False,
        allow_null=True,
    )
    # Include readonly fields to handle cases where they're passed in
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)
    deleted_by = serializers.PrimaryKeyRelatedField(read_only=True)
    last_transferred_at = serializers.DateTimeField(read_only=True)
    polymorphic_ctype = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Item
        fields = (
            "name",
            "description",
            "quantity",
            "campaign",
            "owner",
            "created_by",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "last_transferred_at",
            "polymorphic_ctype",
        )
        read_only_fields = (
            "created_by",
            "created_at",
            "updated_at",
            "is_deleted",
            "deleted_at",
            "deleted_by",
            "last_transferred_at",
            "polymorphic_ctype",
        )

    def __init__(self, *args, **kwargs):
        """Initialize with user-accessible campaigns and characters."""
        super().__init__(*args, **kwargs)

        # For updates, make campaign field truly ignored by removing it
        if self.instance:
            # This is an update - remove campaign field entirely
            self.fields.pop("campaign", None)

        # Set querysets based on user in context
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Only set campaign queryset for creation
            if not self.instance:
                # User can create items in campaigns they're a member of
                user_campaigns = Campaign.objects.filter(
                    models.Q(owner=request.user)
                    | models.Q(memberships__user=request.user)
                ).distinct()
                if "campaign" in self.fields:
                    self.fields["campaign"].queryset = user_campaigns

            # Set character owner queryset
            campaign = None
            campaign_id = self.context.get("campaign_id")
            if campaign_id:
                campaign = Campaign.objects.filter(id=campaign_id).first()
            elif self.instance:
                # For updates, use the instance's campaign
                campaign = self.instance.campaign

            if campaign:
                # Character owner must be in same campaign
                self.fields["owner"].queryset = Character.objects.filter(
                    campaign=campaign
                )

    def validate_name(self, value):
        """Validate item name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Item name cannot be empty.")

        if len(value) > 100:  # Assuming max length from model
            raise serializers.ValidationError("Item name cannot exceed 100 characters.")

        return value.strip()

    def get_polymorphic_ctype(self, obj):
        """Get the polymorphic content type for future subclasses."""
        return {
            "app_label": obj._meta.app_label,
            "model": obj._meta.model_name,
        }

    def validate_quantity(self, value):
        """Validate item quantity."""
        if value is not None and value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    # Removed custom to_internal_value - let DRF handle readonly fields

    def validate(self, data):
        """Validate item data including campaign constraints."""
        # For updates, handle campaign context differently
        if self.instance:  # Updating existing item
            campaign = self.instance.campaign
            # Remove campaign from validation data since it's readonly for updates
            data.pop("campaign", None)
        else:  # Creating new item
            campaign = data.get("campaign")
            if not campaign:
                raise serializers.ValidationError(
                    {"campaign": ["Campaign is required."]}
                )

            # Check if user can create items in this campaign
            request = self.context.get("request")
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError(ErrorMessages.UNAUTHORIZED)

            user = request.user
            user_role = campaign.get_user_role(user)

            # Only campaign members with PLAYER+ role can create items
            if user_role is None:
                raise serializers.ValidationError(
                    {
                        "campaign": [
                            "You don't have permission to create items "
                            "in this campaign."
                        ]
                    }
                )
            elif user_role == "OBSERVER":
                raise serializers.ValidationError(
                    {"campaign": ["Observers cannot create items."]}
                )

        # Validate character ownership
        owner = data.get("owner")
        if owner and owner.campaign != campaign:
            raise serializers.ValidationError(
                {"owner": ["Item owner must be a character in the same campaign."]}
            )

        return data

    def create(self, validated_data):
        """Create item with proper audit user."""
        request = self.context.get("request")
        item = Item(**validated_data)
        item.save(user=request.user)
        return item

    def update(self, instance, validated_data):
        """Update item with audit trail."""
        request = self.context.get("request")

        # Remove readonly fields from validated_data if present
        readonly_fields = [
            "campaign",
            "created_by",
            "created_at",
            "updated_at",
            "deleted_at",
            "deleted_by",
            "is_deleted",
            "last_transferred_at",
            "polymorphic_ctype",
        ]
        for field in readonly_fields:
            validated_data.pop(field, None)

        # Check if owner is being changed to handle transfer
        new_owner = validated_data.get("owner")
        owner_changed = new_owner != instance.owner

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Save all changes first
        instance.save(user=request.user)

        # If owner changed, update transfer timestamp
        if owner_changed:
            from django.utils import timezone

            instance.last_transferred_at = timezone.now()
            instance.save(update_fields=["last_transferred_at"], user=request.user)

        return instance

    def to_representation(self, instance):
        """Return full item representation."""
        # Use the main ItemSerializer for response
        serializer = ItemSerializer(instance, context=self.context)
        return serializer.data


# Scene API serializers
class SceneCampaignSerializer(serializers.ModelSerializer):
    """Lightweight campaign serializer for scene responses."""

    class Meta:
        model = Campaign
        fields = ("id", "name")


class SceneCharacterSerializer(serializers.ModelSerializer):
    """Lightweight character serializer for scene participants."""

    player_owner = UserSerializer(read_only=True)

    class Meta:
        model = Character
        fields = ("id", "name", "npc", "player_owner")


class SceneCreatedBySerializer(serializers.ModelSerializer):
    """Lightweight user serializer for scene creator responses."""

    class Meta:
        model = User
        fields = ("id", "username")


class SceneSerializer(serializers.ModelSerializer):
    """
    Base serializer for Scene model with nested relationships.

    Includes campaign, participants, and creator information for
    comprehensive scene management.
    """

    campaign = SceneCampaignSerializer(read_only=True)
    participants = SceneCharacterSerializer(many=True, read_only=True)
    created_by = SceneCreatedBySerializer(read_only=True)
    participant_count = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Scene
        fields = (
            "id",
            "name",
            "description",
            "status",
            "status_display",
            "campaign",
            "participants",
            "participant_count",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status_display",
            "campaign",
            "participants",
            "participant_count",
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_participant_count(self, obj):
        """
        Get the total number of participants in this scene.

        Uses len() on prefetched participants to avoid additional query.
        """
        # Check if participants are prefetched
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "participants" in obj._prefetched_objects_cache
        ):
            return len(obj.participants.all())
        return obj.participants.count()

    def get_status_display(self, obj):
        """Get the human-readable status display."""
        return obj.get_status_display()


class SceneDetailSerializer(SceneSerializer):
    """
    Extended serializer for Scene detail views with additional information.

    Includes full participant details and scene management context.
    """

    can_manage = serializers.SerializerMethodField()
    can_participate = serializers.SerializerMethodField()

    class Meta(SceneSerializer.Meta):
        fields = SceneSerializer.Meta.fields + ("can_manage", "can_participate")

    def get_can_manage(self, obj):
        """Check if the current user can manage this scene."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        user_role = obj.campaign.get_user_role(request.user)
        return user_role in ["OWNER", "GM"]

    def get_can_participate(self, obj):
        """Check if the current user can participate in this scene."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        user_role = obj.campaign.get_user_role(request.user)
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]


class SceneCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating scenes."""

    campaign = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.objects.none(),  # Will be set in view
        write_only=True,
        required=False,  # Not required for updates
    )
    participants = serializers.PrimaryKeyRelatedField(
        # Use all characters, validate in validate_participants
        queryset=Character.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Scene
        fields = (
            "name",
            "description",
            "status",
            "campaign",
            "participants",
        )

    def __init__(self, *args, **kwargs):
        """Initialize with optimized queryset setting."""
        super().__init__(*args, **kwargs)

        # For updates, remove campaign field to make it read-only
        if self.instance:
            self.fields.pop("campaign", None)

        # Set querysets based on user context with optimization
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user = request.user

            # Only set campaign queryset for creation
            if not self.instance and "campaign" in self.fields:
                # Optimized user campaigns query
                self.fields["campaign"].queryset = Campaign.objects.filter(
                    models.Q(owner=user) | models.Q(memberships__user=user)
                ).distinct()

            # Note: participants queryset is now set to all characters
            # and validation is handled in validate_participants method

    def _get_target_campaign(self):
        """Get the target campaign for this operation."""
        # Check context first for explicit campaign_id
        campaign_id = self.context.get("campaign_id")
        if campaign_id:
            try:
                return Campaign.objects.get(id=campaign_id)
            except Campaign.DoesNotExist:
                return None

        # For updates, use instance campaign
        if self.instance:
            return self.instance.campaign

        return None

    def validate_name(self, value):
        """Validate scene name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Scene name cannot be empty.")

        if len(value) > 200:  # Assuming max length from model
            raise serializers.ValidationError(
                "Scene name cannot exceed 200 characters."
            )

        return value.strip()

    def validate_status(self, value):
        """Validate status transitions."""
        if self.instance and value != self.instance.status:
            # Check valid status transitions
            valid_transitions = {
                "ACTIVE": ["CLOSED"],
                "CLOSED": ["ARCHIVED"],
                "ARCHIVED": [],
            }

            current_status = self.instance.status
            if value not in valid_transitions.get(current_status, []):
                if current_status == "ARCHIVED":
                    raise serializers.ValidationError(
                        "Archived scenes cannot be changed."
                    )
                elif current_status == "ACTIVE" and value == "ARCHIVED":
                    raise serializers.ValidationError(
                        "Cannot archive an active scene. Close it first."
                    )
                elif current_status == "CLOSED" and value == "ACTIVE":
                    raise serializers.ValidationError(
                        "Cannot reactivate a closed scene."
                    )
                else:
                    raise serializers.ValidationError(
                        f"Invalid status transition from {current_status} to {value}."
                    )

        return value

    def validate_participants(self, value):
        """Validate that participants belong to the correct campaign."""
        if not value:
            return value

        campaign = self._get_target_campaign()
        if not campaign:
            # For creation, get campaign from data
            campaign_data = self.initial_data.get("campaign")
            if campaign_data:
                try:
                    campaign = Campaign.objects.get(pk=int(campaign_data))
                except (Campaign.DoesNotExist, ValueError, TypeError):
                    raise serializers.ValidationError("Invalid campaign.")

        if campaign:
            for participant in value:
                if participant.campaign != campaign:
                    raise serializers.ValidationError(
                        f"Character '{participant.name}' must be in the same campaign."
                    )

        return value

    def validate(self, data):
        """Validate scene data including campaign constraints."""
        # For updates, handle campaign context differently
        if self.instance:  # Updating existing scene
            campaign = self.instance.campaign
            # Remove campaign from validation data since it's readonly for updates
            data.pop("campaign", None)
        else:  # Creating new scene
            campaign = data.get("campaign")
            if not campaign:
                raise serializers.ValidationError(
                    {"campaign": ["Campaign is required."]}
                )

            # Check if user can create scenes in this campaign
            request = self.context.get("request")
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError(ErrorMessages.UNAUTHORIZED)

            user = request.user
            user_role = campaign.get_user_role(user)

            # Only OWNER and GM can create scenes
            if user_role not in ["OWNER", "GM"]:
                if user_role in ["PLAYER", "OBSERVER"]:
                    raise serializers.ValidationError(
                        {
                            "campaign": [
                                "Only campaign owners and GMs can create scenes."
                            ]
                        }
                    )
                else:
                    raise serializers.ValidationError(
                        {
                            "campaign": [
                                "You don't have permission to create scenes "
                                "in this campaign."
                            ]
                        }
                    )

        return data

    def create(self, validated_data):
        """Create scene with proper audit user and participants."""
        request = self.context.get("request")
        participants_data = validated_data.pop("participants", [])

        scene = Scene(**validated_data)
        scene.created_by = request.user
        scene.save()

        # Add participants
        if participants_data:
            scene.participants.set(participants_data)

        return scene

    def update(self, instance, validated_data):
        """Update scene with audit trail and participant management."""
        participants_data = validated_data.pop("participants", None)

        # Remove readonly fields from validated_data if present
        readonly_fields = [
            "campaign",
            "created_by",
            "created_at",
            "updated_at",
        ]
        for field in readonly_fields:
            validated_data.pop(field, None)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Save changes
        instance.save()

        # Update participants if provided
        if participants_data is not None:
            instance.participants.set(participants_data)

        return instance

    def to_representation(self, instance):
        """Return full scene representation."""
        # Use the main SceneSerializer for response
        serializer = SceneSerializer(instance, context=self.context)
        return serializer.data


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model in API responses.

    Provides comprehensive message data with nested relationships
    for scene message history display.
    """

    scene = serializers.SerializerMethodField()
    character = serializers.SerializerMethodField()
    sender = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "scene",
            "character",
            "sender",
            "content",
            "message_type",
            "recipients",
            "created_at",
        )
        read_only_fields = (
            "id",
            "scene",
            "character",
            "sender",
            "recipients",
            "timestamp",
        )

    def get_scene(self, obj):
        """Get minimal scene information."""
        if obj.scene:
            return {
                "id": obj.scene.id,
                "name": obj.scene.name,
            }
        return None

    def get_character(self, obj):
        """Get character information if present."""
        if obj.character:
            return {
                "id": obj.character.id,
                "name": obj.character.name,
                "npc": obj.character.npc,
            }
        return None

    def get_sender(self, obj):
        """Get sender information."""
        if obj.sender:
            return {
                "id": obj.sender.id,
                "username": obj.sender.username,
                "display_name": getattr(
                    obj.sender, "display_name", obj.sender.username
                ),
            }
        return None

    def get_recipients(self, obj):
        """Get recipients for private messages."""
        if obj.message_type == "PRIVATE":
            return [
                {
                    "id": recipient.id,
                    "username": recipient.username,
                    "display_name": getattr(
                        recipient, "display_name", recipient.username
                    ),
                }
                for recipient in obj.recipients.all()
            ]
        return []


# Password Reset serializers
class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.CharField(max_length=254)

    def validate_email(self, value):
        """Validate email field (can be email or username)."""
        if not value or value.strip() == "":
            raise serializers.ValidationError("Email or username is required.")

        # Clean whitespace
        value = value.strip()

        # Check length
        if len(value) > 254:
            raise serializers.ValidationError("Email/username is too long.")

        # Basic format validation - reject obviously invalid formats
        # but allow usernames and valid emails
        if "@" in value:
            # If it has @, it should be a valid email format
            from django.core.exceptions import ValidationError as DjangoValidationError
            from django.core.validators import validate_email

            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")
        else:
            # It's a username - do basic username validation
            # Require usernames to start with letter/number and contain only alphanumeric and underscore
            import re

            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_]*$", value) or len(value) < 1:
                raise serializers.ValidationError("Invalid email or username format.")

        return value.lower()  # Normalize case

    def save(self):
        """Create password reset for user if they exist."""
        email = self.validated_data["email"]

        # Try to find user by email first, then by username
        user = None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username__iexact=email)
            except User.DoesNotExist:
                pass

        if user and user.is_active:
            # Create password reset (this will invalidate existing resets)
            reset = PasswordReset.objects.create_for_user(user)
            return reset

        # Return None for non-existent or inactive users
        # (but don't reveal this information)
        return None


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField(max_length=64, min_length=64)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_token(self, value):
        """Validate token format."""
        if not value:
            raise serializers.ValidationError("Token is required.")

        if len(value) != 64:
            raise serializers.ValidationError("Invalid token format.")

        # Check if token is valid hex
        try:
            int(value, 16)
        except ValueError:
            raise serializers.ValidationError("Invalid token format.")

        return value

    def validate_new_password(self, value):
        """Validate new password strength."""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

        return value

    def validate(self, data):
        """Cross-field validation."""
        # Check password confirmation match
        if data.get("new_password") != data.get("new_password_confirm"):
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )

        # Validate token exists and is valid
        token = data.get("token")
        if token:
            reset = PasswordReset.objects.get_valid_reset_by_token(token)
            if not reset:
                raise serializers.ValidationError(
                    {"token": "Password reset token is invalid or has expired."}
                )
            # Check if user is active
            if not reset.user.is_active:
                raise serializers.ValidationError(
                    {"token": "User account is inactive."}
                )
            data["_reset"] = reset  # Store for save method

        return data

    def save(self):
        """Reset the user's password and mark token as used."""
        reset = self.validated_data["_reset"]
        new_password = self.validated_data["new_password"]

        # Reset password
        user = reset.user
        user.set_password(new_password)
        user.save()

        # Mark token as used
        reset.mark_as_used()

        return user


class PasswordResetTokenValidationSerializer(serializers.Serializer):
    """Serializer for password reset token validation."""

    token = serializers.CharField(max_length=64, min_length=64)

    def validate_token(self, value):
        """Validate token format and existence."""
        if not value:
            raise serializers.ValidationError("Token is required.")

        if len(value) != 64:
            raise serializers.ValidationError("Invalid token format.")

        # Check if token is valid hex
        try:
            int(value, 16)
        except ValueError:
            raise serializers.ValidationError("Invalid token format.")

        return value


# Session Management serializers
class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for UserSession model."""

    is_current = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    time_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = (
            "id",
            "ip_address",
            "user_agent",
            "device_type",
            "browser",
            "operating_system",
            "location",
            "is_active",
            "remember_me",
            "created_at",
            "last_activity",
            "ended_at",
            "is_current",
            "expires_at",
            "time_until_expiry",
        )
        read_only_fields = (
            "id",
            "ip_address",
            "user_agent",
            "device_type",
            "browser",
            "operating_system",
            "location",
            "is_active",
            "remember_me",
            "created_at",
            "last_activity",
            "ended_at",
            "is_current",
            "expires_at",
            "time_until_expiry",
        )

    def get_is_current(self, obj):
        """Check if this is the current session."""
        request = self.context.get("request")
        if request and hasattr(request, "session"):
            return obj.session.session_key == request.session.session_key
        return False

    def get_expires_at(self, obj):
        """Get session expiry time."""
        return obj.session.expire_date

    def get_time_until_expiry(self, obj):
        """Get time until session expires."""
        from django.utils import timezone

        if obj.session.expire_date > timezone.now():
            return (obj.session.expire_date - timezone.now()).total_seconds()
        return 0


class SessionSecurityLogSerializer(serializers.ModelSerializer):
    """Serializer for SessionSecurityLog model."""

    class Meta:
        model = SessionSecurityLog
        fields = (
            "id",
            "event_type",
            "ip_address",
            "user_agent",
            "details",
            "timestamp",
        )
        read_only_fields = (
            "id",
            "event_type",
            "ip_address",
            "user_agent",
            "details",
            "timestamp",
        )


class CurrentSessionSerializer(UserSessionSerializer):
    """Extended serializer for current session info with security events."""

    recent_security_events = serializers.SerializerMethodField()

    class Meta(UserSessionSerializer.Meta):
        fields = UserSessionSerializer.Meta.fields + ("recent_security_events",)

    def get_recent_security_events(self, obj):
        """Get recent security events for this session."""
        recent_events = SessionSecurityLog.objects.filter(user_session=obj).recent(
            hours=24
        )[:10]

        return SessionSecurityLogSerializer(recent_events, many=True).data


class SessionExtendSerializer(serializers.Serializer):
    """Serializer for session extension requests."""

    hours = serializers.IntegerField(
        default=24,
        min_value=1,
        max_value=720,  # Max 30 days
        help_text="Number of hours to extend the session",
    )


class TerminateAllSessionsResponseSerializer(serializers.Serializer):
    """Serializer for terminate all sessions response."""

    terminated_sessions = serializers.IntegerField(read_only=True)
