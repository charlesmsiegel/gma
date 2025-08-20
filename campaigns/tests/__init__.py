# Import all test classes to make them discoverable by Django's test runner

# Campaign creation tests
from .test_gm_permissions import GMPermissionLimitationsTest
from .test_invitation_permissions import InvitationPermissionTest
from .test_owner_protection import OwnerProtectionTest

# Permission validation tests
from .test_permission_matrix import (
    CampaignPermissionMatrixTest,
    CrossCampaignPermissionTest,
)

# Campaign API tests
from .test_views_api import CampaignDetailAPIViewTest, CampaignListAPIViewTest
from .test_views_creation import CampaignCreateViewTest

# Campaign detail view tests
from .test_views_detail import CampaignDetailViewEnhancedTest, CampaignDetailViewTest

# Campaign form tests
from .test_views_forms import CampaignFormTest

# Campaign list view tests
from .test_views_list import CampaignListViewTest

# Campaign management tests
from .test_views_management import (
    CampaignManagementEdgeCaseTest,
    CampaignManagementURLTest,
)

__all__ = [
    # Creation tests
    "CampaignCreateViewTest",
    # Detail view tests
    "CampaignDetailViewEnhancedTest",
    "CampaignDetailViewTest",
    # Management tests
    "CampaignManagementEdgeCaseTest",
    "CampaignManagementURLTest",
    # List view tests
    "CampaignListViewTest",
    # Form tests
    "CampaignFormTest",
    # API tests
    "CampaignDetailAPIViewTest",
    "CampaignListAPIViewTest",
    # Permission validation tests
    "CampaignPermissionMatrixTest",
    "CrossCampaignPermissionTest",
    "GMPermissionLimitationsTest",
    "InvitationPermissionTest",
    "OwnerProtectionTest",
]
