"""
Tests for SourceReference relationship functionality.

This module tests relationship functionality including:
- GenericForeignKey relationships to various models
- Book ForeignKey relationships
- Multiple references handling
- Relationship cascading behavior

Part of the comprehensive SourceReference test suite from GitHub issue #181.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character
from core.models import Book, SourceReference

User = get_user_model()


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
