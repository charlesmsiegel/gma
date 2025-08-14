"""
API serializers for the GMA application.
"""

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers

from campaigns.models import Campaign, CampaignInvitation, CampaignMembership
from characters.models import Character

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


class CharacterCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating characters."""

    campaign = serializers.PrimaryKeyRelatedField(
        queryset=Campaign.objects.none(),  # Will be set in view
        write_only=True,
        required=False  # Not required for updates
    )

    class Meta:
        model = Character
        fields = (
            "name",
            "description",
            "campaign",
        )

    def __init__(self, *args, **kwargs):
        """Initialize with user-accessible campaigns."""
        super().__init__(*args, **kwargs)
        
        # Set campaign queryset based on user in context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # User can create characters in campaigns they're a member of
            user_campaigns = Campaign.objects.filter(
                models.Q(owner=request.user) |
                models.Q(memberships__user=request.user)
            ).distinct()
            self.fields['campaign'].queryset = user_campaigns

    def validate_name(self, value):
        """Validate character name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Character name cannot be empty.")
        
        if len(value) > 100:
            raise serializers.ValidationError("Character name cannot exceed 100 characters.")
        
        name = value.strip()
        
        # Check uniqueness for creation or when name changes during update
        if self.context.get('request'):
            request = self.context['request']
            
            # Get campaign for uniqueness check
            if not self.instance:  # Creating new character
                # This will be set by the parent validate method after this field validation runs
                # For now, we can't check uniqueness at field level for creation
                pass
            else:  # Updating existing character
                campaign = self.instance.campaign
                # Check if this name conflicts with another character
                existing_qs = Character.all_objects.filter(campaign=campaign, name=name)
                existing_qs = existing_qs.exclude(pk=self.instance.pk)
                
                if existing_qs.exists():
                    raise serializers.ValidationError(
                        "A character with this name already exists in this campaign."
                    )
        
        return name

    def validate(self, data):
        """Validate character data including uniqueness and campaign limits."""
        # Get campaign for validation
        if not self.instance:  # Creating new character
            campaign = data.get('campaign')
            if not campaign:
                raise serializers.ValidationError({"campaign": ["Campaign is required."]})

            # Get the user from context
            request = self.context.get('request')
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError("Authentication required.")

            user = request.user

            # Campaign membership is checked in the view's perform_create method

            # Check character limit for the campaign
            if campaign.max_characters_per_player > 0:
                existing_count = Character.objects.filter(
                    campaign=campaign, 
                    player_owner=user
                ).count()
                    
                if existing_count >= campaign.max_characters_per_player:
                    raise serializers.ValidationError({
                        "campaign": [
                            f"You cannot have more than {campaign.max_characters_per_player} "
                            f"character{'s' if campaign.max_characters_per_player != 1 else ''} "
                            "in this campaign."
                        ]
                    })
        else:  # Updating existing character
            campaign = self.instance.campaign
            
        # Check character name uniqueness within campaign - this is critical validation
        name = data.get('name', '').strip()
        if name and campaign:
            # Use all_objects to include soft-deleted characters in uniqueness check
            existing_qs = Character.all_objects.filter(campaign=campaign, name=name)
            if self.instance:
                existing_qs = existing_qs.exclude(pk=self.instance.pk)
            
            if existing_qs.exists():
                # This should prevent the model constraint validation from running
                raise serializers.ValidationError({
                    "name": ["A character with this name already exists in this campaign."]
                })

        return data

    def create(self, validated_data):
        """Create character with proper owner and game system."""
        from django.db import IntegrityError
        from django.core.exceptions import ValidationError
        
        request = self.context.get('request')
        campaign = validated_data['campaign']
        
        # Set player_owner and game_system
        validated_data['player_owner'] = request.user
        validated_data['game_system'] = campaign.game_system
        
        # Create character with audit user
        try:
            character = Character(**validated_data)
            # Skip model validation since serializer validation already handled it
            character.save(audit_user=request.user, validate=False)
            return character
        except IntegrityError as e:
            error_message = str(e)
            if 'unique_character_name_per_campaign' in error_message:
                raise serializers.ValidationError({
                    "name": ["A character with this name already exists in this campaign."]
                })
            raise
        except ValidationError as e:
            # Handle Django model validation errors
            if hasattr(e, 'error_dict'):
                # Check for name-specific errors first
                if 'name' in e.error_dict:
                    raise serializers.ValidationError({
                        "name": [str(error) for error in e.error_dict['name']]
                    })
                # Check for constraint violations in non_field_errors
                elif '__all__' in e.error_dict:
                    for error in e.error_dict['__all__']:
                        error_msg = str(error)
                        if ('Campaign and Name' in error_msg and 'unique' in error_msg.lower()) or \
                           ('fields campaign, name must make a unique set' in error_msg) or \
                           ('campaign, name must make a unique set' in error_msg) or \
                           ('The fields campaign, name must make a unique set' in error_msg):
                            raise serializers.ValidationError({
                                "name": ["A character with this name already exists in this campaign."]
                            })
            # Check for single error messages as well
            if hasattr(e, 'message'):
                error_msg = str(e.message)
                if ('Campaign and Name' in error_msg and 'unique' in error_msg.lower()):
                    raise serializers.ValidationError({
                        "name": ["A character with this name already exists in this campaign."]
                    })
            # Re-raise the original error if we can't handle it
            raise

    def update(self, instance, validated_data):
        """Update character with audit trail."""
        from django.db import IntegrityError
        from django.core.exceptions import ValidationError
        
        request = self.context.get('request')
        
        # Remove campaign from validated_data if present (shouldn't be changed)
        validated_data.pop('campaign', None)
        
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
            if 'unique_character_name_per_campaign' in error_message:
                raise serializers.ValidationError({
                    "name": ["A character with this name already exists in this campaign."]
                })
            raise
        except ValidationError as e:
            # Handle Django model validation errors
            if hasattr(e, 'error_dict'):
                # Check for name-specific errors first
                if 'name' in e.error_dict:
                    raise serializers.ValidationError({
                        "name": [str(error) for error in e.error_dict['name']]
                    })
                # Check for constraint violations in non_field_errors
                elif '__all__' in e.error_dict:
                    for error in e.error_dict['__all__']:
                        error_msg = str(error)
                        if ('Campaign and Name' in error_msg and 'unique' in error_msg.lower()) or \
                           ('fields campaign, name must make a unique set' in error_msg) or \
                           ('campaign, name must make a unique set' in error_msg) or \
                           ('The fields campaign, name must make a unique set' in error_msg):
                            raise serializers.ValidationError({
                                "name": ["A character with this name already exists in this campaign."]
                            })
            # Check for single error messages as well
            if hasattr(e, 'message'):
                error_msg = str(e.message)
                if ('Campaign and Name' in error_msg and 'unique' in error_msg.lower()):
                    raise serializers.ValidationError({
                        "name": ["A character with this name already exists in this campaign."]
                    })
            # Re-raise the original error if we can't handle it
            raise

    def to_representation(self, instance):
        """Return full character representation."""
        # Use the main CharacterSerializer for response
        serializer = CharacterSerializer(instance, context=self.context)
        return serializer.data
