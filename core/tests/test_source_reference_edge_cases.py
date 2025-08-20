"""
Tests for SourceReference edge cases and error handling.

This module tests edge cases, error conditions, and boundary conditions including:
- Field validation edge cases
- Error handling scenarios
- Special character handling
- Timestamp functionality

Part of the comprehensive SourceReference test suite from GitHub issue #181.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character
from core.models import Book, SourceReference

User = get_user_model()


class SourceReferenceEdgeCasesTest(TestCase):
    """Test edge cases and boundary conditions for SourceReference model."""

    def setUp(self):
        """Set up test data for edge case tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.book = Book.objects.create(
            title="Test Book",
            abbreviation="TB",
            system="Test System",
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Test System",
            max_characters_per_player=0,  # Unlimited characters
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

    def test_empty_chapter_field(self):
        """Test creating source reference with empty chapter field."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            chapter="",
        )

        self.assertEqual(source_ref.chapter, "")

    def test_maximum_page_number(self):
        """Test source reference with very large page number."""
        large_page = 99999
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=large_page,
        )

        self.assertEqual(source_ref.page_number, large_page)

    def test_special_characters_in_chapter(self):
        """Test handling of special characters in chapter field."""
        special_chapter = "Chapter 3: Traditions — The Order of Hermes & Sons of Ether"
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            chapter=special_chapter,
        )

        self.assertEqual(source_ref.chapter, special_chapter)
        self.assertIn("—", source_ref.chapter)
        self.assertIn("&", source_ref.chapter)

    def test_unicode_characters_in_chapter(self):
        """Test handling of unicode characters in chapter field."""
        unicode_chapter = "Capítulo 3: Tradições — A Ordem de Hermes"
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            chapter=unicode_chapter,
        )

        self.assertEqual(source_ref.chapter, unicode_chapter)

    def test_long_chapter_name(self):
        """Test source reference with very long chapter name."""
        long_chapter = "A" * 500  # Very long chapter name
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            chapter=long_chapter,
        )

        self.assertEqual(source_ref.chapter, long_chapter)

    def test_whitespace_handling_in_chapter(self):
        """Test handling of whitespace in chapter field."""
        chapter_with_whitespace = "  Chapter 3: Traditions  "
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            chapter=chapter_with_whitespace,
        )

        # Django doesn't automatically strip whitespace, so it should be preserved
        self.assertEqual(source_ref.chapter, chapter_with_whitespace)

    def test_none_values_for_optional_fields(self):
        """Test that None values work correctly for optional fields."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=None,
            chapter=None,
        )

        self.assertIsNone(source_ref.page_number)
        # chapter field is nullable, so None stays None
        self.assertIsNone(source_ref.chapter)


class SourceReferenceErrorHandlingTest(TestCase):
    """Test error handling and validation for SourceReference model."""

    def setUp(self):
        """Set up test data for error handling tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.book = Book.objects.create(
            title="Test Book",
            abbreviation="TB",
            system="Test System",
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Test System",
            max_characters_per_player=0,  # Unlimited characters
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

    def test_missing_book_raises_error(self):
        """Test that missing book field raises appropriate error."""
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                source_ref = SourceReference(
                    content_object=self.character,
                    # book is missing
                )
                source_ref.full_clean()
                source_ref.save()

    def test_missing_content_object_raises_error(self):
        """Test that missing content_object raises appropriate error."""
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                source_ref = SourceReference(
                    book=self.book,
                    # content_object is missing
                )
                source_ref.full_clean()
                source_ref.save()

    def test_invalid_page_number_type_raises_error(self):
        """Test that invalid page number types raise validation errors."""
        # String instead of integer
        with self.assertRaises((ValidationError, ValueError)):
            source_ref = SourceReference(
                book=self.book,
                content_object=self.character,
                page_number="not_a_number",
            )
            source_ref.full_clean()

    def test_float_page_number_handling(self):
        """Test that float page numbers are handled appropriately."""
        # Django may store floats as-is in some database backends
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=42.9,
        )
        # The actual behavior may vary by database backend
        self.assertTrue(isinstance(source_ref.page_number, (int, float)))
        self.assertGreaterEqual(source_ref.page_number, 42)

    def test_page_number_negative_value_rejected(self):
        """Test that negative page numbers are properly rejected."""
        with self.assertRaises((ValidationError, IntegrityError)):
            with transaction.atomic():
                SourceReference.objects.create(
                    book=self.book,
                    content_object=self.character,
                    page_number=-1,  # Should be rejected by PositiveIntegerField
                )


class SourceReferenceTimestampTest(TestCase):
    """Test timestamp functionality from TimestampedMixin."""

    def setUp(self):
        """Set up test data for timestamp tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.book = Book.objects.create(
            title="Test Book",
            abbreviation="TB",
            system="Test System",
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Test System",
            max_characters_per_player=0,  # Unlimited characters
        )
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

    def test_created_at_set_on_creation(self):
        """Test that created_at is set when source reference is created."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        self.assertIsNotNone(source_ref.created_at)

    def test_updated_at_set_on_creation(self):
        """Test that updated_at is set when source reference is created."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        self.assertIsNotNone(source_ref.updated_at)

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when source reference is modified."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        original_updated_at = source_ref.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        source_ref.page_number = 42
        source_ref.save()

        source_ref.refresh_from_db()
        self.assertGreater(source_ref.updated_at, original_updated_at)

    def test_created_at_unchanged_on_update(self):
        """Test that created_at doesn't change when source reference is updated."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        original_created_at = source_ref.created_at

        source_ref.page_number = 42
        source_ref.save()

        source_ref.refresh_from_db()
        self.assertEqual(source_ref.created_at, original_created_at)
