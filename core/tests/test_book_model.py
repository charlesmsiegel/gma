"""
Comprehensive tests for the Book model.

Tests cover all requirements from GitHub issue #177:
- Book model with title, abbreviation, system, edition fields
- Publisher, ISBN, URL fields for metadata
- Unique constraints on title and abbreviation
- String representation shows abbreviation and title
- Ordering by system, then title

This test suite follows the project's TDD principles with comprehensive coverage
including model creation, validation, constraints, edge cases, and error handling.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase


# Test model for Book - defined here since the actual model doesn't exist yet
class Book(models.Model):
    """
    Model for storing canonical RPG source books.

    This is a test model that defines the expected structure based on the requirements.
    The actual model should be implemented in core/models/sources.py.
    """

    title = models.CharField(
        max_length=200, unique=True, help_text="Full title of the book"
    )
    abbreviation = models.CharField(
        max_length=20,
        unique=True,
        help_text=(
            "Short abbreviation for the book (e.g., 'M20' for Mage 20th Anniversary)"
        ),
    )
    system = models.CharField(
        max_length=100,
        help_text="Game system this book belongs to (e.g., 'Mage: The Ascension')",
    )
    edition = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Edition information (e.g., 'Revised', '20th Anniversary')",
    )
    publisher = models.CharField(
        max_length=100, blank=True, default="", help_text="Publisher of the book"
    )
    isbn = models.CharField(
        max_length=17,  # ISBN-13 with hyphens: 978-0-123456-78-9
        blank=True,
        default="",
        help_text="ISBN-10 or ISBN-13 of the book",
    )
    url = models.URLField(
        blank=True, default="", help_text="URL to purchase or learn more about the book"
    )

    class Meta:
        app_label = "core"
        ordering = ["system", "title"]

    def __str__(self):
        return f"{self.abbreviation} - {self.title}"


class BookModelTest(TestCase):
    """Test basic Book model functionality."""

    def test_book_creation_with_required_fields(self):
        """Test creating a book with only required fields."""
        book = Book.objects.create(
            title="Mage: The Ascension 20th Anniversary Edition",
            abbreviation="M20",
            system="Mage: The Ascension",
        )

        self.assertEqual(book.title, "Mage: The Ascension 20th Anniversary Edition")
        self.assertEqual(book.abbreviation, "M20")
        self.assertEqual(book.system, "Mage: The Ascension")
        self.assertEqual(book.edition, "")  # Default value
        self.assertEqual(book.publisher, "")  # Default value
        self.assertEqual(book.isbn, "")  # Default value
        self.assertEqual(book.url, "")  # Default value

    def test_book_creation_with_all_fields(self):
        """Test creating a book with all fields populated."""
        book = Book.objects.create(
            title="Mage: The Ascension 20th Anniversary Edition",
            abbreviation="M20",
            system="Mage: The Ascension",
            edition="20th Anniversary",
            publisher="Onyx Path Publishing",
            isbn="978-1-58846-475-3",
            url=(
                "https://www.drivethrurpg.com/product/149562/"
                "Mage-the-Ascension-20th-Anniversary-Edition"
            ),
        )

        self.assertEqual(book.title, "Mage: The Ascension 20th Anniversary Edition")
        self.assertEqual(book.abbreviation, "M20")
        self.assertEqual(book.system, "Mage: The Ascension")
        self.assertEqual(book.edition, "20th Anniversary")
        self.assertEqual(book.publisher, "Onyx Path Publishing")
        self.assertEqual(book.isbn, "978-1-58846-475-3")
        self.assertEqual(
            book.url,
            (
                "https://www.drivethrurpg.com/product/149562/"
                "Mage-the-Ascension-20th-Anniversary-Edition"
            ),
        )

    def test_book_str_representation(self):
        """Test that string representation shows abbreviation and title."""
        book = Book.objects.create(
            title="Mage: The Ascension 20th Anniversary Edition",
            abbreviation="M20",
            system="Mage: The Ascension",
        )

        expected_str = "M20 - Mage: The Ascension 20th Anniversary Edition"
        self.assertEqual(str(book), expected_str)
        self.assertEqual(book.__str__(), expected_str)

    def test_book_str_with_special_characters(self):
        """Test string representation with special characters and unicode."""
        book = Book.objects.create(
            title="Wraith: The Oblivion Players Guide — 2nd Edition",
            abbreviation="WrPG2",
            system="Wraith: The Oblivion",
        )

        expected_str = "WrPG2 - Wraith: The Oblivion Players Guide — 2nd Edition"
        self.assertEqual(str(book), expected_str)


class BookFieldValidationTest(TestCase):
    """Test field validation for the Book model."""

    def test_title_required_field(self):
        """Test that title field is required."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        title_field = fields["title"]

        self.assertFalse(title_field.blank)
        self.assertFalse(title_field.null)
        self.assertEqual(title_field.max_length, 200)

    def test_abbreviation_required_field(self):
        """Test that abbreviation field is required."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        abbreviation_field = fields["abbreviation"]

        self.assertFalse(abbreviation_field.blank)
        self.assertFalse(abbreviation_field.null)
        self.assertEqual(abbreviation_field.max_length, 20)

    def test_system_required_field(self):
        """Test that system field is required."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        system_field = fields["system"]

        self.assertFalse(system_field.blank)
        self.assertFalse(system_field.null)
        self.assertEqual(system_field.max_length, 100)

    def test_edition_optional_field(self):
        """Test that edition field is optional."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        edition_field = fields["edition"]

        self.assertTrue(edition_field.blank)
        self.assertEqual(edition_field.default, "")
        self.assertEqual(edition_field.max_length, 50)

    def test_publisher_optional_field(self):
        """Test that publisher field is optional."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        publisher_field = fields["publisher"]

        self.assertTrue(publisher_field.blank)
        self.assertEqual(publisher_field.default, "")
        self.assertEqual(publisher_field.max_length, 100)

    def test_isbn_optional_field(self):
        """Test that isbn field is optional."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        isbn_field = fields["isbn"]

        self.assertTrue(isbn_field.blank)
        self.assertEqual(isbn_field.default, "")
        self.assertEqual(isbn_field.max_length, 17)

    def test_url_optional_field(self):
        """Test that url field is optional and is URLField."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        url_field = fields["url"]

        self.assertTrue(url_field.blank)
        self.assertEqual(url_field.default, "")
        self.assertIsInstance(url_field, models.URLField)

    def test_url_field_validation(self):
        """Test that URL field validates proper URLs."""
        # Valid URLs should work
        valid_urls = [
            "https://www.drivethrurpg.com/product/149562/test",
            "http://example.com",
            "https://onyx-path.com/products/mage-20th",
            "ftp://files.example.com/book.pdf",
        ]

        for url in valid_urls:
            book = Book(
                title="Test Book", abbreviation="TB", system="Test System", url=url
            )
            try:
                book.full_clean()  # This validates the URL field
            except ValidationError:
                self.fail(f"Valid URL {url} failed validation")

    def test_url_field_invalid_validation(self):
        """Test that URL field rejects invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "just text",
            "www.example.com",  # Missing protocol
            "://missing-domain.com",
        ]

        for url in invalid_urls:
            book = Book(
                title="Test Book", abbreviation="TB", system="Test System", url=url
            )
            with self.assertRaises(ValidationError):
                book.full_clean()


class BookUniqueConstraintTest(TestCase):
    """Test unique constraints on Book model fields."""

    def setUp(self):
        """Create a test book for constraint testing."""
        self.existing_book = Book.objects.create(
            title="Mage: The Ascension 20th Anniversary Edition",
            abbreviation="M20",
            system="Mage: The Ascension",
        )

    def test_title_unique_constraint(self):
        """Test that title field has unique constraint."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        title_field = fields["title"]

        self.assertTrue(title_field.unique)

    def test_title_unique_constraint_violation(self):
        """Test that duplicate titles are not allowed."""
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                title="Mage: The Ascension 20th Anniversary Edition",  # Duplicate title
                abbreviation="M20-DUPE",
                system="Mage: The Ascension",
            )

    def test_abbreviation_unique_constraint(self):
        """Test that abbreviation field has unique constraint."""
        fields = {f.name: f for f in Book._meta.get_fields()}
        abbreviation_field = fields["abbreviation"]

        self.assertTrue(abbreviation_field.unique)

    def test_abbreviation_unique_constraint_violation(self):
        """Test that duplicate abbreviations are not allowed."""
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                title="Different Title",
                abbreviation="M20",  # Duplicate abbreviation
                system="Mage: The Ascension",
            )

    def test_case_sensitive_uniqueness(self):
        """Test that uniqueness constraints are case-sensitive."""
        # Different case should be allowed (this is Django's default behavior)
        Book.objects.create(
            title="mage: the ascension 20th anniversary edition",  # Different case
            abbreviation="m20",  # Different case
            system="Mage: The Ascension",
        )

        # Should succeed without IntegrityError
        self.assertEqual(Book.objects.count(), 2)

    def test_duplicate_non_unique_fields_allowed(self):
        """Test that non-unique fields can have duplicate values."""
        # Same system, edition, publisher should be allowed
        Book.objects.create(
            title="Book of Shadows: Mage Players Guide",
            abbreviation="BoS",
            system="Mage: The Ascension",  # Same system as existing book
            edition="2nd Edition",
            publisher="White Wolf Publishing",
        )

        Book.objects.create(
            title="Sons of Ether Tradition Book",
            abbreviation="SoE",
            system="Mage: The Ascension",  # Same system again
            edition="2nd Edition",  # Same edition
            publisher="White Wolf Publishing",  # Same publisher
        )

        self.assertEqual(Book.objects.count(), 3)


class BookOrderingTest(TestCase):
    """Test the ordering behavior of Book model."""

    def setUp(self):
        """Create test books for ordering tests."""
        # Create books in non-alphabetical order to test ordering
        self.book_vampire = Book.objects.create(
            title="Vampire: The Masquerade 20th Anniversary Edition",
            abbreviation="V20",
            system="Vampire: The Masquerade",
        )

        self.book_mage2 = Book.objects.create(
            title="Tradition Book: Order of Hermes",
            abbreviation="ToH",
            system="Mage: The Ascension",
        )

        self.book_mage1 = Book.objects.create(
            title="Mage: The Ascension 20th Anniversary Edition",
            abbreviation="M20",
            system="Mage: The Ascension",
        )

        self.book_werewolf = Book.objects.create(
            title="Werewolf: The Apocalypse 20th Anniversary Edition",
            abbreviation="W20",
            system="Werewolf: The Apocalypse",
        )

    def test_model_ordering_meta(self):
        """Test that model has correct ordering in Meta class."""
        self.assertEqual(Book._meta.ordering, ["system", "title"])

    def test_default_ordering_by_system_then_title(self):
        """Test that books are ordered by system, then title by default."""
        books = list(Book.objects.all())

        expected_order = [
            self.book_mage1,  # Mage: The Ascension (first system alphabetically)
            self.book_mage2,  # Mage: The Ascension (second title alphabetically)
            self.book_vampire,  # Vampire: The Masquerade
            self.book_werewolf,  # Werewolf: The Apocalypse
        ]

        self.assertEqual(books, expected_order)

    def test_ordering_with_same_system_different_titles(self):
        """Test ordering when books have the same system."""
        mage_books = list(Book.objects.filter(system="Mage: The Ascension"))

        # Should be ordered by title within the same system
        self.assertEqual(len(mage_books), 2)
        self.assertEqual(
            mage_books[0], self.book_mage1
        )  # "Mage: The..." comes before "Tradition..."
        self.assertEqual(mage_books[1], self.book_mage2)

    def test_explicit_ordering_override(self):
        """Test that explicit ordering can override default ordering."""
        # Order by abbreviation instead
        books_by_abbrev = list(Book.objects.order_by("abbreviation"))

        expected_order = [
            self.book_mage1,  # M20
            self.book_mage2,  # ToH
            self.book_vampire,  # V20
            self.book_werewolf,  # W20
        ]

        self.assertEqual(books_by_abbrev, expected_order)

    def test_reverse_ordering(self):
        """Test reverse ordering."""
        books_reverse = list(Book.objects.order_by("-system", "-title"))

        expected_order = [
            self.book_werewolf,  # Werewolf (last system alphabetically)
            self.book_vampire,  # Vampire
            self.book_mage2,  # Mage (second title reverse alphabetically)
            self.book_mage1,  # Mage (first title reverse alphabetically)
        ]

        self.assertEqual(books_reverse, expected_order)


class BookEdgeCasesTest(TestCase):
    """Test edge cases and boundary conditions for Book model."""

    def test_empty_optional_fields(self):
        """Test creating book with empty optional fields."""
        book = Book.objects.create(
            title="Test Book",
            abbreviation="TB",
            system="Test System",
            edition="",
            publisher="",
            isbn="",
            url="",
        )

        self.assertEqual(book.edition, "")
        self.assertEqual(book.publisher, "")
        self.assertEqual(book.isbn, "")
        self.assertEqual(book.url, "")

    def test_maximum_length_fields(self):
        """Test fields at their maximum length."""
        long_title = "A" * 200  # Max length for title
        long_abbreviation = "B" * 20  # Max length for abbreviation
        long_system = "C" * 100  # Max length for system
        long_edition = "D" * 50  # Max length for edition
        long_publisher = "E" * 100  # Max length for publisher
        long_isbn = "F" * 17  # Max length for ISBN

        book = Book.objects.create(
            title=long_title,
            abbreviation=long_abbreviation,
            system=long_system,
            edition=long_edition,
            publisher=long_publisher,
            isbn=long_isbn,
            url="https://example.com",
        )

        self.assertEqual(book.title, long_title)
        self.assertEqual(book.abbreviation, long_abbreviation)
        self.assertEqual(book.system, long_system)
        self.assertEqual(book.edition, long_edition)
        self.assertEqual(book.publisher, long_publisher)
        self.assertEqual(book.isbn, long_isbn)

    def test_special_characters_in_fields(self):
        """Test handling of special characters in text fields."""
        book = Book.objects.create(
            title="Mage: The Ascension — Player's Guide™",
            abbreviation="M:A-PG",
            system="Mage: The Ascension (1st Edition)",
            edition="2nd & Revised",
            publisher="White Wolf Publishing, Inc.",
            isbn="978-1-58846-475-3",
        )

        self.assertIn("—", book.title)
        self.assertIn("™", book.title)
        self.assertIn(":", book.abbreviation)
        self.assertIn("-", book.abbreviation)
        self.assertIn("(", book.system)
        self.assertIn(")", book.system)
        self.assertIn("&", book.edition)
        self.assertIn(",", book.publisher)
        self.assertIn(".", book.publisher)
        self.assertIn("-", book.isbn)

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        book = Book.objects.create(
            title="Guía del Jugador de Mago: La Ascensión",
            abbreviation="GJM:LA",
            system="Mago: La Ascensión",
            publisher="La Factoría de Ideas",
        )

        self.assertEqual(book.title, "Guía del Jugador de Mago: La Ascensión")
        self.assertEqual(book.system, "Mago: La Ascensión")
        self.assertEqual(book.publisher, "La Factoría de Ideas")

    def test_isbn_formats(self):
        """Test various ISBN formats."""
        isbn_formats = [
            "0123456789",  # ISBN-10 without hyphens
            "0-123-45678-9",  # ISBN-10 with hyphens
            "9781234567890",  # ISBN-13 without hyphens
            "978-1-234-56789-0",  # ISBN-13 with hyphens
            "979-0-123456-78-9",  # ISBN-13 with 979 prefix
        ]

        for i, isbn in enumerate(isbn_formats):
            book = Book.objects.create(
                title=f"Test Book {i}",
                abbreviation=f"TB{i}",
                system="Test System",
                isbn=isbn,
            )
            self.assertEqual(book.isbn, isbn)

    def test_long_url(self):
        """Test handling of long URLs."""
        long_url = (
            "https://www.drivethrurpg.com/product/149562/"
            "Mage-the-Ascension-20th-Anniversary-Edition-Players-Guide-"
            "with-extremely-long-title-and-parameters?"
            "affiliate_id=123456&campaign=test&utm_source=test&"
            "utm_medium=test&utm_campaign=test"
        )

        book = Book.objects.create(
            title="Test Book", abbreviation="TB", system="Test System", url=long_url
        )

        self.assertEqual(book.url, long_url)


class BookModelErrorHandlingTest(TestCase):
    """Test error handling and validation for Book model."""

    def test_missing_required_fields(self):
        """Test that missing required fields raise appropriate errors."""
        # Test missing title
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                book = Book(abbreviation="TB", system="Test System")
                book.full_clean()
                book.save()

        # Test missing abbreviation
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                book = Book(title="Test Book", system="Test System")
                book.full_clean()
                book.save()

        # Test missing system
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                book = Book(title="Test Book", abbreviation="TB")
                book.full_clean()
                book.save()

    def test_field_length_violations(self):
        """Test that exceeding field length limits raises validation errors."""
        # Test title too long
        with self.assertRaises(ValidationError):
            book = Book(
                title="A" * 201,  # One character too long
                abbreviation="TB",
                system="Test System",
            )
            book.full_clean()

        # Test abbreviation too long
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                abbreviation="B" * 21,  # One character too long
                system="Test System",
            )
            book.full_clean()

        # Test system too long
        with self.assertRaises(ValidationError):
            book = Book(
                title="Test Book",
                abbreviation="TB",
                system="C" * 101,  # One character too long
            )
            book.full_clean()

    def test_invalid_url_formats(self):
        """Test that invalid URL formats raise validation errors."""
        invalid_urls = [
            "not a url",
            "ftp://",
            "http://",
            "://example.com",
            "http:///path",
            "http://.",
            "http://..",
        ]

        for invalid_url in invalid_urls:
            with self.assertRaises(ValidationError):
                book = Book(
                    title="Test Book",
                    abbreviation="TB",
                    system="Test System",
                    url=invalid_url,
                )
                book.full_clean()

    def test_whitespace_handling(self):
        """Test handling of whitespace in fields."""
        book = Book.objects.create(
            title="  Mage: The Ascension  ",  # Leading/trailing whitespace
            abbreviation="  M20  ",
            system="  Mage: The Ascension  ",
        )

        # Django doesn't automatically strip whitespace, so it should be preserved
        self.assertEqual(book.title, "  Mage: The Ascension  ")
        self.assertEqual(book.abbreviation, "  M20  ")
        self.assertEqual(book.system, "  Mage: The Ascension  ")

    def test_default_values_for_optional_fields(self):
        """Test that optional fields use default values correctly."""
        # Test that optional fields default to empty string when not provided
        book = Book.objects.create(
            title="Test Book",
            abbreviation="TB",
            system="Test System",
            # Optional fields not provided
        )

        # Fields with default="" should have empty string
        self.assertEqual(book.edition, "")
        self.assertEqual(book.publisher, "")
        self.assertEqual(book.isbn, "")
        self.assertEqual(book.url, "")


class BookQueryTest(TestCase):
    """Test querying and filtering of Book model."""

    def setUp(self):
        """Create test data for query tests."""
        self.mage_books = [
            Book.objects.create(
                title="Mage: The Ascension 20th Anniversary Edition",
                abbreviation="M20",
                system="Mage: The Ascension",
                edition="20th Anniversary",
                publisher="Onyx Path Publishing",
            ),
            Book.objects.create(
                title="Book of Shadows: Mage Players Guide",
                abbreviation="BoS",
                system="Mage: The Ascension",
                edition="Revised",
                publisher="White Wolf Publishing",
            ),
        ]

        self.vampire_book = Book.objects.create(
            title="Vampire: The Masquerade 20th Anniversary Edition",
            abbreviation="V20",
            system="Vampire: The Masquerade",
            edition="20th Anniversary",
            publisher="Modiphius Entertainment",
        )

    def test_filter_by_system(self):
        """Test filtering books by game system."""
        mage_books = Book.objects.filter(system="Mage: The Ascension")
        self.assertEqual(mage_books.count(), 2)
        self.assertIn(self.mage_books[0], mage_books)
        self.assertIn(self.mage_books[1], mage_books)

        vampire_books = Book.objects.filter(system="Vampire: The Masquerade")
        self.assertEqual(vampire_books.count(), 1)
        self.assertEqual(vampire_books.first(), self.vampire_book)

    def test_filter_by_edition(self):
        """Test filtering books by edition."""
        anniversary_books = Book.objects.filter(edition="20th Anniversary")
        self.assertEqual(anniversary_books.count(), 2)

        revised_books = Book.objects.filter(edition="Revised")
        self.assertEqual(revised_books.count(), 1)
        self.assertEqual(revised_books.first(), self.mage_books[1])

    def test_filter_by_publisher(self):
        """Test filtering books by publisher."""
        onyx_books = Book.objects.filter(publisher="Onyx Path Publishing")
        self.assertEqual(onyx_books.count(), 1)
        self.assertEqual(onyx_books.first(), self.mage_books[0])

    def test_search_by_title_partial(self):
        """Test searching books by partial title match."""
        mage_titles = Book.objects.filter(title__icontains="Mage")
        self.assertEqual(mage_titles.count(), 2)

        ascension_titles = Book.objects.filter(title__icontains="Ascension")
        self.assertEqual(ascension_titles.count(), 1)
        self.assertEqual(ascension_titles.first(), self.mage_books[0])

    def test_search_by_abbreviation(self):
        """Test searching books by abbreviation."""
        m20_book = Book.objects.filter(abbreviation="M20")
        self.assertEqual(m20_book.count(), 1)
        self.assertEqual(m20_book.first(), self.mage_books[0])

    def test_complex_query(self):
        """Test complex queries with multiple filters."""
        # Find all 20th Anniversary books from Onyx Path Publishing
        complex_query = Book.objects.filter(
            edition="20th Anniversary", publisher="Onyx Path Publishing"
        )
        self.assertEqual(complex_query.count(), 1)
        self.assertEqual(complex_query.first(), self.mage_books[0])

    def test_ordering_in_queries(self):
        """Test that default ordering applies to query results."""
        all_books = list(Book.objects.all())

        # Should be ordered by system, then title
        self.assertEqual(len(all_books), 3)
        # First two should be Mage books (ordered by title)
        self.assertEqual(
            all_books[0], self.mage_books[1]
        )  # "Book of Shadows..." comes first
        self.assertEqual(
            all_books[1], self.mage_books[0]
        )  # "Mage: The Ascension..." comes second
        # Third should be Vampire book
        self.assertEqual(all_books[2], self.vampire_book)
