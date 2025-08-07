# Campaign Permission System

This document describes the campaign-based permission system implemented for the Game Master Application.

## Permission Hierarchy

The permission system follows a hierarchical model with the following roles, listed from highest to lowest permissions:

1. **Owner** - Campaign creator/owner
2. **GM** - Game Master (can have multiple per campaign)
3. **Player** - Active participant in the campaign
4. **Observer** - Read-only access to campaign content

## Permission Classes (Django REST Framework)

### `IsCampaignOwner`
- Allows access only to campaign owners
- Used for campaign management operations (delete, transfer ownership, etc.)

### `IsCampaignGM`
- Allows access only to campaign Game Masters
- Used for GM-specific operations (scene management, NPC control, etc.)

### `IsCampaignMember`
- Allows access to any campaign member (GM, Player, or Observer)
- Used for general campaign content access

### `IsCampaignOwnerOrGM`
- Allows access to campaign owners or Game Masters
- Used for administrative operations that both owners and GMs can perform

## View Mixins and Decorators

### `CampaignPermissionMixin`
A mixin class that provides helper methods for campaign permission checking in Django class-based views.

**Methods:**
- `get_campaign()`: Retrieves campaign from URL kwargs, raises Http404 if not found
- `check_campaign_permission(user, level)`: Checks user permission level

### Class Decorators

#### `@require_campaign_owner`
Decorates a view class to require campaign owner permissions.

```python
@require_campaign_owner
class DeleteCampaignView(View):
    def post(self, request, campaign_id):
        # Only campaign owner can access this
        pass
```

#### `@require_campaign_gm`
Decorates a view class to require GM permissions.

```python
@require_campaign_gm
class ManageNPCView(View):
    def get(self, request, campaign_id):
        # Only campaign GMs can access this
        pass
```

#### `@require_campaign_member`
Decorates a view class to require any membership in the campaign.

```python
@require_campaign_member
class ViewCampaignContentView(View):
    def get(self, request, campaign_id):
        # Any campaign member can access this
        pass
```

#### `@require_campaign_owner_or_gm`
Decorates a view class to require owner or GM permissions.

```python
@require_campaign_owner_or_gm
class ManageCampaignSettingsView(View):
    def get(self, request, campaign_id):
        # Campaign owner or GM can access this
        pass
```

## Usage Examples

### Django REST Framework Views

```python
from rest_framework.views import APIView
from campaigns.permissions import IsCampaignMember

class CampaignDetailView(APIView):
    permission_classes = [IsCampaignMember]

    def get(self, request, campaign_id):
        # Access campaign details
        pass
```

### Django Class-Based Views

```python
from django.views import View
from campaigns.permissions import require_campaign_owner

@require_campaign_owner
class CampaignDeleteView(View):
    def post(self, request, campaign_id):
        # Delete campaign
        pass
```

### Manual Permission Checking

```python
from campaigns.permissions import CampaignPermissionMixin

class MyCampaignView(CampaignPermissionMixin, View):
    def get(self, request, campaign_id):
        # Check permission manually
        self.check_campaign_permission(request.user, "member")

        # Get campaign object
        campaign = self.get_campaign()

        # Continue with view logic
        pass
```

## Security Features

### Resource Hiding
All permission denials return **404 Not Found** instead of **403 Forbidden** to hide the existence of resources from unauthorized users.

### Active Campaign Check
Only active campaigns (is_active=True) are accessible through the permission system. Inactive campaigns return 404.

### Anonymous User Handling
Anonymous users are automatically denied access to all campaign resources.

## Model Methods

The Campaign model provides convenience methods for permission checking:

```python
campaign = Campaign.objects.get(id=1)

# Check specific roles
campaign.is_owner(user)      # True if user owns the campaign
campaign.is_gm(user)         # True if user is a GM
campaign.is_player(user)     # True if user is a player
campaign.is_observer(user)   # True if user is an observer
campaign.is_member(user)     # True if user has any membership

# Get user's role
role = campaign.get_user_role(user)  # Returns 'owner', 'gm', 'player', 'observer', or None
```

## URL Pattern Requirements

For the permission system to work correctly, your URL patterns must include the campaign ID parameter:

```python
urlpatterns = [
    path('campaigns/<int:campaign_id>/scenes/', views.CampaignScenesView.as_view()),
    path('campaigns/<int:campaign_id>/characters/', views.CampaignCharactersView.as_view()),
    # etc.
]
```

The permission classes and mixins will automatically extract the `campaign_id` from the URL kwargs.
