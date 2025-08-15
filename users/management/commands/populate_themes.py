"""
Management command to populate initial theme data.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import Theme


class Command(BaseCommand):
    help = "Populate initial theme data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset all themes (delete existing and recreate)",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Deleting existing themes...")
            Theme.objects.all().delete()

        # Define theme data based on existing CSS themes
        themes_data = [
            {
                "name": "light",
                "display_name": "Light",
                "description": "Clean and bright theme perfect for daytime use",
                "category": "standard",
                "primary_color": "#0d6efd",
                "background_color": "#ffffff",
                "text_color": "#212529",
                "is_dark_theme": False,
                "is_high_contrast": False,
                "is_default": True,
                "sort_order": 1,
            },
            {
                "name": "dark",
                "display_name": "Dark",
                "description": "GitHub-inspired dark mode for comfortable nighttime use",
                "category": "dark",
                "primary_color": "#58a6ff",
                "background_color": "#0d1117",
                "text_color": "#f0f6fc",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 2,
            },
            {
                "name": "forest",
                "display_name": "Forest",
                "description": "Nature-inspired green theme for a calming experience",
                "category": "fantasy",
                "primary_color": "#28a745",
                "background_color": "#1a2e05",
                "text_color": "#e8f5e8",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 3,
            },
            {
                "name": "ocean",
                "display_name": "Ocean",
                "description": "Deep blue theme reminiscent of ocean depths",
                "category": "modern",
                "primary_color": "#17a2b8",
                "background_color": "#002644",
                "text_color": "#e6f3ff",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 4,
            },
            {
                "name": "sunset",
                "display_name": "Sunset",
                "description": "Warm orange and red tones like a beautiful sunset",
                "category": "modern",
                "primary_color": "#fd7e14",
                "background_color": "#2d1b0e",
                "text_color": "#fff3e0",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 5,
            },
            {
                "name": "midnight",
                "display_name": "Midnight",
                "description": "Deep purple theme for the night owls",
                "category": "dark",
                "primary_color": "#6f42c1",
                "background_color": "#1a0d2e",
                "text_color": "#f0eeff",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 6,
            },
            {
                "name": "lavender",
                "display_name": "Lavender",
                "description": "Soft purple theme with a gentle, soothing feel",
                "category": "standard",
                "primary_color": "#8e44ad",
                "background_color": "#faf9ff",
                "text_color": "#2c1810",
                "is_dark_theme": False,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 7,
            },
            {
                "name": "mint",
                "display_name": "Mint",
                "description": "Fresh green and white theme with a clean aesthetic",
                "category": "standard",
                "primary_color": "#20c997",
                "background_color": "#f8fffc",
                "text_color": "#0f2922",
                "is_dark_theme": False,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 8,
            },
            {
                "name": "high-contrast",
                "display_name": "High Contrast",
                "description": "Maximum contrast theme for improved accessibility",
                "category": "accessibility",
                "primary_color": "#0066cc",
                "background_color": "#ffffff",
                "text_color": "#000000",
                "is_dark_theme": False,
                "is_high_contrast": True,
                "is_default": False,
                "sort_order": 9,
            },
            {
                "name": "warm",
                "display_name": "Warm",
                "description": "Warm earth tones for a cozy feeling",
                "category": "vintage",
                "primary_color": "#d63384",
                "background_color": "#fff8f5",
                "text_color": "#3d2914",
                "is_dark_theme": False,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 10,
            },
            {
                "name": "gothic",
                "display_name": "Gothic",
                "description": "Dark and mysterious theme perfect for World of Darkness",
                "category": "fantasy",
                "primary_color": "#dc3545",
                "background_color": "#1c1c1c",
                "text_color": "#e6e6e6",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 11,
            },
            {
                "name": "cyberpunk",
                "display_name": "Cyberpunk",
                "description": "Neon-inspired theme with futuristic vibes",
                "category": "modern",
                "primary_color": "#00ff00",
                "background_color": "#0a0a0a",
                "text_color": "#00ff88",
                "is_dark_theme": True,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 12,
            },
            {
                "name": "vintage",
                "display_name": "Vintage",
                "description": "Classic sepia tones for a nostalgic feel",
                "category": "vintage",
                "primary_color": "#8B4513",
                "background_color": "#faf6f0",
                "text_color": "#3c2414",
                "is_dark_theme": False,
                "is_high_contrast": False,
                "is_default": False,
                "sort_order": 13,
            },
        ]

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for theme_data in themes_data:
                theme, created = Theme.objects.get_or_create(
                    name=theme_data["name"], defaults=theme_data
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Created theme: {theme.display_name}")
                    )
                else:
                    # Update existing theme with new data
                    for key, value in theme_data.items():
                        if key != "name":  # Don't update the name
                            setattr(theme, key, value)
                    theme.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"Updated theme: {theme.display_name}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {created_count + updated_count} themes "
                f"({created_count} created, {updated_count} updated)"
            )
        )

        # Ensure only one default theme exists
        default_themes = Theme.objects.filter(is_default=True)
        if default_themes.count() > 1:
            # Keep the first one, unset others
            for theme in default_themes[1:]:
                theme.is_default = False
                theme.save()
            self.stdout.write(self.style.WARNING("Fixed multiple default themes"))
        elif default_themes.count() == 0:
            # Set light theme as default
            light_theme = Theme.objects.filter(name="light").first()
            if light_theme:
                light_theme.is_default = True
                light_theme.save()
                self.stdout.write(self.style.SUCCESS("Set light theme as default"))
