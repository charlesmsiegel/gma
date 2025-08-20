"""
Test package for API endpoints.
"""

# Import all test classes to make them discoverable by Django's test runner

# Character API tests
from .test_character_api_base import BaseCharacterAPITestCase
from .test_character_api_crud import (
    CharacterCreateAPITest,
    CharacterDeleteAPITest,
    CharacterDetailAPITest,
    CharacterUpdateAPITest,
)
from .test_character_api_list import CharacterListAPITest
from .test_character_api_specialized import (
    CharacterAPIErrorHandlingTest,
    CharacterPolymorphicSerializationTest,
)

__all__ = [
    # Base test case
    "BaseCharacterAPITestCase",
    # Character API tests
    "CharacterListAPITest",
    "CharacterCreateAPITest",
    "CharacterDetailAPITest",
    "CharacterUpdateAPITest",
    "CharacterDeleteAPITest",
    "CharacterPolymorphicSerializationTest",
    "CharacterAPIErrorHandlingTest",
]
