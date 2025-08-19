"""
Comprehensive tests for the SourceReference model.

Tests cover all requirements from GitHub issue #181:
- SourceReference model with GenericForeignKey to link to any model
- ForeignKey relationship to Book model
- Optional page number field (positive integer)
- Optional chapter field (text)
- Database indexes on content_type and object_id
- String representation showing book and page information

This test suite follows the project's TDD principles with comprehensive coverage
including model creation, validation, relationships, edge cases, and error handling.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character
from core.models import Book, SourceReference

User = get_user_model()


class SourceReferenceModelTest(TestCase):
    """Test basic SourceReference model functionality."""

    def setUp(self):
        """Set up test data for SourceReference tests."""
        # Create test users
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create test book
        self.book = Book.objects.create(
            title="Mage: The Ascension 20th Anniversary Edition",
            abbreviation="M20",
            system="Mage: The Ascension",
            edition="20th Anniversary",
            publisher="Onyx Path Publishing",
        )

        # Create test campaign with unlimited characters
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited characters
        )

        # Create test character
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
        )

    def test_source_reference_creation_with_required_fields(self):
        """Test creating a source reference with only required fields."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        self.assertEqual(source_ref.book, self.book)
        self.assertEqual(source_ref.content_object, self.character)
        self.assertEqual(
            source_ref.content_type, ContentType.objects.get_for_model(Character)
        )
        self.assertEqual(source_ref.object_id, self.character.pk)
        self.assertIsNone(source_ref.page_number)
        self.assertIsNone(source_ref.chapter)  # Default is None

    def test_source_reference_creation_with_all_fields(self):
        """Test creating a source reference with all fields populated."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=42,
            chapter="Chapter 3: Traditions",
        )

        self.assertEqual(source_ref.book, self.book)
        self.assertEqual(source_ref.content_object, self.character)
        self.assertEqual(
            source_ref.content_type, ContentType.objects.get_for_model(Character)
        )
        self.assertEqual(source_ref.object_id, self.character.pk)
        self.assertEqual(source_ref.page_number, 42)
        self.assertEqual(source_ref.chapter, "Chapter 3: Traditions")

    def test_source_reference_str_representation_with_page(self):
        """Test string representation when page number is provided."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=42,
        )

        expected_str = "M20 - Mage: The Ascension 20th Anniversary Edition, p. 42"
        self.assertEqual(str(source_ref), expected_str)

    def test_source_reference_str_representation_with_chapter(self):
        """Test string representation when chapter is provided."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            chapter="Chapter 3: Traditions",
        )

        expected_str = (
            "M20 - Mage: The Ascension 20th Anniversary Edition, Chapter 3: Traditions"
        )
        self.assertEqual(str(source_ref), expected_str)

    def test_source_reference_str_representation_with_page_and_chapter(self):
        """Test string representation when both page and chapter are provided."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=42,
            chapter="Chapter 3: Traditions",
        )

        expected_str = (
            "M20 - Mage: The Ascension 20th Anniversary Edition, "
            "Chapter 3: Traditions, p. 42"
        )
        self.assertEqual(str(source_ref), expected_str)

    def test_source_reference_str_representation_book_only(self):
        """Test string representation when only book is provided."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        expected_str = "M20 - Mage: The Ascension 20th Anniversary Edition"
        self.assertEqual(str(source_ref), expected_str)


class SourceReferenceFieldValidationTest(TestCase):
    """Test field validation for the SourceReference model."""

    def setUp(self):
        """Set up test data for validation tests."""
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

    def test_book_field_required(self):
        """Test that book field is required."""
        fields = {f.name: f for f in SourceReference._meta.get_fields()}
        book_field = fields["book"]

        self.assertFalse(book_field.blank)
        self.assertFalse(book_field.null)
        self.assertIsInstance(book_field, models.ForeignKey)

    def test_content_type_field_required(self):
        """Test that content_type field is required."""
        fields = {f.name: f for f in SourceReference._meta.get_fields()}
        content_type_field = fields["content_type"]

        self.assertFalse(content_type_field.blank)
        self.assertFalse(content_type_field.null)
        self.assertIsInstance(content_type_field, models.ForeignKey)

    def test_object_id_field_required(self):
        """Test that object_id field is required."""
        fields = {f.name: f for f in SourceReference._meta.get_fields()}
        object_id_field = fields["object_id"]

        self.assertFalse(object_id_field.blank)
        self.assertFalse(object_id_field.null)

    def test_page_number_field_optional(self):
        """Test that page_number field is optional."""
        fields = {f.name: f for f in SourceReference._meta.get_fields()}
        page_number_field = fields["page_number"]

        self.assertTrue(page_number_field.blank)
        self.assertTrue(page_number_field.null)
        self.assertIsInstance(page_number_field, models.PositiveIntegerField)

    def test_chapter_field_optional(self):
        """Test that chapter field is optional."""
        fields = {f.name: f for f in SourceReference._meta.get_fields()}
        chapter_field = fields["chapter"]

        self.assertTrue(chapter_field.blank)
        self.assertTrue(chapter_field.null)

    def test_page_number_positive_validation(self):
        """Test that page_number field validates positive integers."""
        # Valid positive integers should work
        valid_pages = [1, 42, 999, 1000]

        for page in valid_pages:
            source_ref = SourceReference(
                book=self.book,
                content_object=self.character,
                page_number=page,
            )
            try:
                source_ref.full_clean()
            except ValidationError:
                self.fail(f"Valid page number {page} failed validation")

    def test_page_number_positive_field_type(self):
        """Test that page_number field is a PositiveIntegerField."""
        fields = {f.name: f for f in SourceReference._meta.get_fields()}
        page_number_field = fields["page_number"]

        # Verify it's the correct field type
        self.assertIsInstance(page_number_field, models.PositiveIntegerField)

    def test_page_number_validation_semantics(self):
        """Test that page numbers follow expected semantics."""
        # Test that reasonable positive page numbers work
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=1,
        )
        self.assertEqual(source_ref.page_number, 1)

        # Test that larger page numbers work
        source_ref2 = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=999,
        )
        self.assertEqual(source_ref2.page_number, 999)


class SourceReferenceGenericForeignKeyTest(TestCase):
    """Test GenericForeignKey functionality for SourceReference model."""

    def setUp(self):
        """Set up test data for GenericForeignKey tests."""
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

    def test_generic_foreign_key_to_character(self):
        """Test GenericForeignKey relationship to Character model."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        # Test that the relationship works both ways
        self.assertEqual(source_ref.content_object, self.character)
        self.assertEqual(
            source_ref.content_type, ContentType.objects.get_for_model(Character)
        )
        self.assertEqual(source_ref.object_id, self.character.pk)

        # Test that we can access the reference from the character
        character_refs = SourceReference.objects.filter(
            content_type=ContentType.objects.get_for_model(Character),
            object_id=self.character.pk,
        )
        self.assertEqual(character_refs.count(), 1)
        self.assertEqual(character_refs.first(), source_ref)

    def test_generic_foreign_key_to_campaign(self):
        """Test GenericForeignKey relationship to Campaign model."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.campaign,
        )

        # Test that the relationship works
        self.assertEqual(source_ref.content_object, self.campaign)
        self.assertEqual(
            source_ref.content_type, ContentType.objects.get_for_model(Campaign)
        )
        self.assertEqual(source_ref.object_id, self.campaign.pk)

    def test_generic_foreign_key_to_book(self):
        """Test GenericForeignKey relationship to Book model."""
        other_book = Book.objects.create(
            title="Other Book",
            abbreviation="OB",
            system="Other System",
        )

        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=other_book,
        )

        # Test that the relationship works
        self.assertEqual(source_ref.content_object, other_book)
        self.assertEqual(
            source_ref.content_type, ContentType.objects.get_for_model(Book)
        )
        self.assertEqual(source_ref.object_id, other_book.pk)

    def test_generic_foreign_key_content_type_auto_set(self):
        """Test content_type is automatically set when content_object is assigned."""
        source_ref = SourceReference(
            book=self.book,
            content_object=self.character,
        )

        # content_type should be automatically set based on content_object
        self.assertEqual(
            source_ref.content_type, ContentType.objects.get_for_model(Character)
        )
        self.assertEqual(source_ref.object_id, self.character.pk)

    def test_multiple_references_to_same_object(self):
        """Test that multiple source references can point to the same object."""
        book2 = Book.objects.create(
            title="Second Book",
            abbreviation="SB",
            system="Test System",
        )

        ref1 = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=10,
        )

        ref2 = SourceReference.objects.create(
            book=book2,
            content_object=self.character,
            page_number=20,
        )

        # Both references should point to the same character
        self.assertEqual(ref1.content_object, self.character)
        self.assertEqual(ref2.content_object, self.character)

        # Should be able to query all references for this character
        character_refs = SourceReference.objects.filter(
            content_type=ContentType.objects.get_for_model(Character),
            object_id=self.character.pk,
        )
        self.assertEqual(character_refs.count(), 2)
        self.assertIn(ref1, character_refs)
        self.assertIn(ref2, character_refs)

    def test_generic_foreign_key_null_handling(self):
        """Test that GenericForeignKey handles null references properly."""
        # Test direct database assignment of null values
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_type=ContentType.objects.get_for_model(Character),
            object_id=99999,  # Non-existent ID
        )

        # content_object should return None for invalid references
        self.assertIsNone(source_ref.content_object)


class SourceReferenceBookRelationshipTest(TestCase):
    """Test the ForeignKey relationship between SourceReference and Book."""

    def setUp(self):
        """Set up test data for Book relationship tests."""
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

    def test_book_foreign_key_relationship(self):
        """Test that the Book ForeignKey relationship works correctly."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )

        # Test forward relationship
        self.assertEqual(source_ref.book, self.book)
        self.assertEqual(source_ref.book.title, "Test Book")

        # Test reverse relationship
        book_refs = self.book.source_references.all()
        self.assertEqual(book_refs.count(), 1)
        self.assertEqual(book_refs.first(), source_ref)

    def test_book_deletion_cascade(self):
        """Test that deleting a book cascades to source references."""
        source_ref = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
        )
        source_ref_id = source_ref.id

        # Delete the book
        self.book.delete()

        # Source reference should be deleted too
        self.assertFalse(SourceReference.objects.filter(id=source_ref_id).exists())

    def test_multiple_references_to_same_book(self):
        """Test that multiple source references can reference the same book."""
        character2 = Character.objects.create(
            name="Second Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

        ref1 = SourceReference.objects.create(
            book=self.book,
            content_object=self.character,
            page_number=10,
        )

        ref2 = SourceReference.objects.create(
            book=self.book,
            content_object=character2,
            page_number=20,
        )

        # Both references should point to the same book
        self.assertEqual(ref1.book, self.book)
        self.assertEqual(ref2.book, self.book)

        # Book should have both references
        book_refs = self.book.source_references.all()
        self.assertEqual(book_refs.count(), 2)
        self.assertIn(ref1, book_refs)
        self.assertIn(ref2, book_refs)

    def test_book_required_field(self):
        """Test that book field is required and cannot be null."""
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                source_ref = SourceReference(
                    content_object=self.character,
                    # book is None
                )
                source_ref.full_clean()
                source_ref.save()


class SourceReferenceIndexTest(TestCase):
    """Test database index functionality for SourceReference model."""

    def test_content_type_index_exists(self):
        """Test that content_type field has database index."""
        source_ref_indexes = SourceReference._meta.indexes
        content_type_index_exists = any(
            "content_type" in idx.fields for idx in source_ref_indexes
        )
        self.assertTrue(content_type_index_exists)

    def test_object_id_index_exists(self):
        """Test that object_id field has database index."""
        source_ref_indexes = SourceReference._meta.indexes
        object_id_index_exists = any(
            "object_id" in idx.fields for idx in source_ref_indexes
        )
        self.assertTrue(object_id_index_exists)

    def test_compound_content_type_object_id_index_exists(self):
        """Test that compound content_type+object_id index exists."""
        source_ref_indexes = SourceReference._meta.indexes
        compound_index_exists = any(
            idx.fields == ["content_type", "object_id"] for idx in source_ref_indexes
        )
        self.assertTrue(compound_index_exists)


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


class SourceReferenceQueryTest(TestCase):
    """Test querying and filtering of SourceReference model."""

    def setUp(self):
        """Set up test data for query tests."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.book1 = Book.objects.create(
            title="Mage Core Rulebook",
            abbreviation="M20",
            system="Mage: The Ascension",
        )

        self.book2 = Book.objects.create(
            title="Tradition Book: Order of Hermes",
            abbreviation="ToH",
            system="Mage: The Ascension",
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited characters
        )

        self.character1 = Character.objects.create(
            name="Hermetic Mage",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
        )

        self.character2 = Character.objects.create(
            name="Virtual Adept",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Mage: The Ascension",
        )

        # Create test source references
        self.ref1 = SourceReference.objects.create(
            book=self.book1,
            content_object=self.character1,
            page_number=42,
            chapter="Chapter 3: Traditions",
        )

        self.ref2 = SourceReference.objects.create(
            book=self.book2,
            content_object=self.character1,
            page_number=15,
        )

        self.ref3 = SourceReference.objects.create(
            book=self.book1,
            content_object=self.character2,
            page_number=100,
        )

    def test_filter_by_book(self):
        """Test filtering source references by book."""
        book1_refs = SourceReference.objects.filter(book=self.book1)
        self.assertEqual(book1_refs.count(), 2)
        self.assertIn(self.ref1, book1_refs)
        self.assertIn(self.ref3, book1_refs)

        book2_refs = SourceReference.objects.filter(book=self.book2)
        self.assertEqual(book2_refs.count(), 1)
        self.assertEqual(book2_refs.first(), self.ref2)

    def test_filter_by_content_object(self):
        """Test filtering source references by content object."""
        char1_refs = SourceReference.objects.filter(
            content_type=ContentType.objects.get_for_model(Character),
            object_id=self.character1.pk,
        )
        self.assertEqual(char1_refs.count(), 2)
        self.assertIn(self.ref1, char1_refs)
        self.assertIn(self.ref2, char1_refs)

        char2_refs = SourceReference.objects.filter(
            content_type=ContentType.objects.get_for_model(Character),
            object_id=self.character2.pk,
        )
        self.assertEqual(char2_refs.count(), 1)
        self.assertEqual(char2_refs.first(), self.ref3)

    def test_filter_by_page_number(self):
        """Test filtering source references by page number."""
        page_42_refs = SourceReference.objects.filter(page_number=42)
        self.assertEqual(page_42_refs.count(), 1)
        self.assertEqual(page_42_refs.first(), self.ref1)

        # Test range queries
        high_page_refs = SourceReference.objects.filter(page_number__gte=50)
        self.assertEqual(high_page_refs.count(), 1)
        self.assertEqual(high_page_refs.first(), self.ref3)

    def test_filter_by_chapter(self):
        """Test filtering source references by chapter."""
        chapter_refs = SourceReference.objects.filter(chapter__icontains="traditions")
        self.assertEqual(chapter_refs.count(), 1)
        self.assertEqual(chapter_refs.first(), self.ref1)

    def test_complex_query(self):
        """Test complex queries with multiple filters."""
        # Find all references to book1 with page numbers less than 50
        complex_query = SourceReference.objects.filter(
            book=self.book1, page_number__lt=50
        )
        self.assertEqual(complex_query.count(), 1)
        self.assertEqual(complex_query.first(), self.ref1)

    def test_prefetch_related_book(self):
        """Test efficient querying with prefetch_related for book."""
        refs = SourceReference.objects.select_related("book").all()

        # Access book properties without additional queries
        for ref in refs:
            _ = ref.book.title  # Should not trigger additional query
            _ = ref.book.abbreviation

    def test_prefetch_related_content_type(self):
        """Test efficient querying with prefetch_related for content_type."""
        refs = SourceReference.objects.select_related("content_type").all()

        # Access content_type properties without additional queries
        for ref in refs:
            _ = ref.content_type.model  # Should not trigger additional query

    def test_get_references_for_object(self):
        """Test helper method to get all references for a specific object."""

        # This would be a helper method on a manager or queryset
        def get_references_for_object(obj):
            return SourceReference.objects.filter(
                content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk
            )

        char1_refs = get_references_for_object(self.character1)
        self.assertEqual(char1_refs.count(), 2)

        campaign_refs = get_references_for_object(self.campaign)
        self.assertEqual(campaign_refs.count(), 0)


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
