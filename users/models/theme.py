"""Theme models for the users app."""

from django.core.validators import RegexValidator
from django.db import models


class Theme(models.Model):
    """
    Theme model to make themes first-class objects in the system.

    This model provides rich metadata about themes including descriptions,
    categories, accessibility features, and preview information.
    """

    CATEGORY_CHOICES = [
        ("standard", "Standard"),
        ("dark", "Dark Mode"),
        ("accessibility", "Accessibility"),
        ("fantasy", "Fantasy"),
        ("modern", "Modern"),
        ("vintage", "Vintage"),
    ]

    name: models.CharField = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-z0-9-]+$",
                message="Theme name must contain only lowercase letters, numbers, "
                "and hyphens",
            )
        ],
        help_text="Internal theme identifier (e.g., 'dark', 'forest')",
    )
    display_name: models.CharField = models.CharField(
        max_length=100, help_text="Human-readable theme name"
    )
    description: models.TextField = models.TextField(
        blank=True, help_text="Detailed description of the theme"
    )
    category: models.CharField = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="standard"
    )

    # Visual properties
    primary_color: models.CharField = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Primary color must be a valid hex color code (e.g., #0d6efd)",
            )
        ],
        help_text="Primary color as hex code (e.g., #0d6efd)",
    )
    background_color: models.CharField = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Background color must be a valid hex color code",
            )
        ],
        help_text="Main background color as hex code",
    )
    text_color: models.CharField = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Text color must be a valid hex color code",
            )
        ],
        help_text="Primary text color as hex code",
    )

    # Features and metadata
    is_dark_theme: models.BooleanField = models.BooleanField(
        default=False, help_text="Whether this is a dark theme"
    )
    is_high_contrast: models.BooleanField = models.BooleanField(
        default=False,
        help_text="Whether this theme provides high contrast for accessibility",
    )
    supports_system_preference: models.BooleanField = models.BooleanField(
        default=True,
        help_text="Whether this theme works well with system dark/light mode detection",
    )

    # Status
    is_active: models.BooleanField = models.BooleanField(
        default=True, help_text="Whether this theme is available for selection"
    )
    is_default: models.BooleanField = models.BooleanField(
        default=False, help_text="Whether this is the default theme for new users"
    )

    # Ordering and organization
    sort_order: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0, help_text="Display order in theme selection (lower numbers first)"
    )

    # Timestamps
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_theme"
        ordering = ["sort_order", "display_name"]
        verbose_name = "Theme"
        verbose_name_plural = "Themes"

        constraints = [
            # Ensure only one default theme exists
            models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="unique_default_theme",
            ),
        ]

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs) -> None:
        """Override save to ensure only one default theme."""
        if self.is_default:
            # Remove default status from other themes
            Theme.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_default_theme(cls) -> "Theme | None":
        """Get the default theme."""
        try:
            return cls.objects.get(is_default=True)
        except cls.DoesNotExist:
            # Fallback to light theme if no default is set
            return cls.objects.filter(name="light").first()

    @classmethod
    def get_available_themes(cls) -> "models.QuerySet[Theme]":
        """Get all active themes ordered by sort_order."""
        return cls.objects.filter(is_active=True).order_by("sort_order", "display_name")

    @classmethod
    def get_dark_themes(cls) -> "models.QuerySet[Theme]":
        """Get all active dark themes."""
        return cls.objects.filter(is_active=True, is_dark_theme=True)

    @classmethod
    def get_accessibility_themes(cls) -> "models.QuerySet[Theme]":
        """Get all active high-contrast themes."""
        return cls.objects.filter(is_active=True, is_high_contrast=True)

    def get_css_filename(self) -> str:
        """Get the CSS filename for this theme."""
        return f"{self.name}.css"

    def get_css_path(self) -> str:
        """Get the full CSS path for static files."""
        return f"css/themes/{self.get_css_filename()}"

    def to_dict(self) -> dict[str, str | bool]:
        """Convert theme to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "primary_color": self.primary_color,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "is_dark_theme": self.is_dark_theme,
            "is_high_contrast": self.is_high_contrast,
            "css_path": self.get_css_path(),
        }


class UserThemePreference(models.Model):
    """
    User theme preferences and history.

    Tracks user theme changes and allows for additional theme customizations.
    """

    user: models.OneToOneField = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="theme_preference"
    )
    current_theme: models.ForeignKey = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_with_theme",
    )

    # User preferences
    auto_switch_dark_mode: models.BooleanField = models.BooleanField(
        default=False,
        help_text="Automatically switch between light/dark themes based on system "
        "preference",
    )
    preferred_light_theme: models.ForeignKey = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_light_preference",
        limit_choices_to={"is_dark_theme": False, "is_active": True},
    )
    preferred_dark_theme: models.ForeignKey = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_dark_preference",
        limit_choices_to={"is_dark_theme": True, "is_active": True},
    )

    # Theme customizations (for future extensibility)
    custom_primary_color: models.CharField = models.CharField(
        max_length=7,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Custom primary color must be a valid hex color code",
            )
        ],
        help_text="Override theme primary color",
    )

    # Timestamps
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_theme_preference"
        verbose_name = "User Theme Preference"
        verbose_name_plural = "User Theme Preferences"

    def __str__(self) -> str:
        return f"{self.user.username}'s theme preference"

    def get_effective_theme(self) -> Theme | None:
        """Get the effective theme for the user."""
        if self.current_theme and self.current_theme.is_active:
            return self.current_theme
        return Theme.get_default_theme()

    def get_theme_for_mode(self, is_dark: bool = False) -> Theme | None:
        """Get the appropriate theme for light/dark mode."""
        if is_dark and self.preferred_dark_theme:
            return self.preferred_dark_theme
        elif not is_dark and self.preferred_light_theme:
            return self.preferred_light_theme

        # Fallback to current theme or default
        current = self.get_effective_theme()
        if current.is_dark_theme == is_dark:
            return current

        # Find a suitable fallback
        if is_dark:
            return Theme.get_dark_themes().first() or Theme.get_default_theme()
        else:
            return Theme.objects.filter(is_active=True, is_dark_theme=False).first()
