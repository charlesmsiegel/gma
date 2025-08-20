"""
Tests for basic SourceReference model functionality and field validation.

This module tests core model functionality including:
- Model creation with required and optional fields
- String representation
- Field validation and constraints
- Basic model structure

Part of the comprehensive SourceReference test suite from GitHub issue #181.
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
