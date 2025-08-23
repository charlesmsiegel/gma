"""
Items app tests.

This module contains comprehensive tests for the Item management interface (Issue #54)
and existing Item model functionality (Issue #53).

Test Structure:
- test_models.py: Item model validation, soft delete, character ownership
- test_admin.py: Admin interface and bulk operations
- test_views.py: Web interface views (create, detail, edit, list, delete) - Issue #54
- test_forms.py: Form validation and behavior - Issue #54  
- test_integration.py: Cross-app integration and workflows - Issue #54
- test_bulk_operations.py: Admin bulk operation testing
- test_character_ownership.py: Single character ownership testing
- test_mixin_application.py: Mixin compatibility testing
- test_polymorphic_conversion.py: Polymorphic model conversion testing
"""

# Import all test modules to ensure they're discovered
from .test_admin import *
from .test_bulk_operations import *
from .test_character_ownership import *
from .test_forms import *
from .test_integration import *
from .test_mixin_application import *
from .test_models import *
from .test_polymorphic_conversion import *
from .test_views import *
