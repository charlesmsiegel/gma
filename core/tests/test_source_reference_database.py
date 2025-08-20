"""
Tests for SourceReference database functionality and querying.

This module tests database-specific functionality including:
- Database indexes
- Querying and filtering
- Performance optimizations
- Complex query operations

Part of the comprehensive SourceReference test suite from GitHub issue #181.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character
from core.models import Book, SourceReference

User = get_user_model()


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
