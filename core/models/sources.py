"""
Models for source references and canonical RPG books.

This module contains models for tracking RPG source books, their metadata,
and references for use throughout the application.
"""

import re

from django.core.exceptions import ValidationError
from django.db import models

from .mixins import TimestampedMixin


class Book(TimestampedMixin, models.Model):
    """
    Model for storing canonical RPG source books.

    This model tracks RPG books with their metadata including title, system,
    edition, publisher information, and external references. Used for
    citations and source references throughout the application.
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
        ordering = ["system", "title"]
        indexes = [
            models.Index(fields=["system"]),
            models.Index(fields=["abbreviation"]),  # For fast lookups
            models.Index(fields=["system", "title"]),  # For default ordering
        ]

    def clean(self):
        """Custom validation for Book model."""
        super().clean()

        # Normalize abbreviation to uppercase for consistency
        if self.abbreviation:
            self.abbreviation = self.abbreviation.upper()

        # Validate ISBN format if provided
        if self.isbn and not self._is_valid_isbn(self.isbn):
            raise ValidationError(
                {"isbn": "Invalid ISBN format. Must be ISBN-10 or ISBN-13."}
            )

    def save(self, *args, **kwargs):
        """Override save to ensure clean() is called."""
        self.full_clean()
        super().save(*args, **kwargs)

    def _is_valid_isbn(self, isbn):
        """
        Validate ISBN-10 or ISBN-13 format.

        Supports both formats with or without hyphens/spaces.
        Performs checksum validation for both ISBN-10 and ISBN-13.
        """
        # Remove all non-digit characters except 'X' for ISBN-10
        clean_isbn = re.sub(r"[^0-9X]", "", isbn.upper())

        if len(clean_isbn) == 10:
            return self._validate_isbn10(clean_isbn)
        elif len(clean_isbn) == 13:
            return self._validate_isbn13(clean_isbn)
        else:
            return False

    def _validate_isbn10(self, isbn):
        """Validate ISBN-10 with checksum."""
        if len(isbn) != 10:
            return False

        try:
            total = 0
            for i in range(9):
                total += int(isbn[i]) * (10 - i)

            # Check digit can be 0-9 or X (representing 10)
            check_digit = isbn[9]
            if check_digit == "X":
                total += 10
            else:
                total += int(check_digit)

            return total % 11 == 0
        except (ValueError, IndexError):
            return False

    def _validate_isbn13(self, isbn):
        """Validate ISBN-13 with checksum."""
        if len(isbn) != 13:
            return False

        try:
            total = 0
            for i in range(12):
                digit = int(isbn[i])
                if i % 2 == 0:
                    total += digit
                else:
                    total += digit * 3

            check_digit = int(isbn[12])
            calculated_check = (10 - (total % 10)) % 10

            return check_digit == calculated_check
        except (ValueError, IndexError):
            return False

    def __str__(self):
        return f"{self.abbreviation} - {self.title}"
