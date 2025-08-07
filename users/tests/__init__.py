from .test_admin import UserAdminTest
from .test_models import CustomUserModelTest
from .test_profile_views import (
    ProfileIntegrationTest,
    UserProfileEditViewTest,
    UserProfileFormValidationTest,
    UserProfileViewTest,
)

__all__ = [
    "CustomUserModelTest",
    "UserAdminTest",
    "UserProfileViewTest",
    "UserProfileEditViewTest",
    "UserProfileFormValidationTest",
    "ProfileIntegrationTest",
]
