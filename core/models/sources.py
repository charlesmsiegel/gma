"""
Models for source references and canonical RPG books.

This module contains models for tracking RPG source books, their metadata,
and references for use throughout the application.
"""

from django.db import models


class Book(models.Model):
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

    def __str__(self):
        return f"{self.abbreviation} - {self.title}"
