# Import all test classes to make them discoverable by Django's test runner

# Character form tests
from .test_character_create_forms import CharacterCreateFormTest
from .test_character_delete_forms import CharacterDeleteFormTest
from .test_character_edit_forms import CharacterEditFormTest

__all__ = [
    # Character form tests
    "CharacterCreateFormTest",
    "CharacterEditFormTest",
    "CharacterDeleteFormTest",
]
