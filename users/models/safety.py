"""
User Safety Preferences model for Lines & Veils system.

This module implements the Lines & Veils safety system that allows users to
specify content they want to avoid (lines) or handle carefully (veils).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class UserSafetyPreferences(models.Model):
    """
    User safety preferences for Lines & Veils system.
    
    Lines are hard boundaries - content that should never appear in the game.
    Veils are soft boundaries - content that can happen but should "fade to black".
    
    Privacy levels control who can see a user's safety preferences:
    - private: Only the user can see their preferences
    - gm_only: Only GMs in campaigns the user participates in can see preferences
    - campaign_members: All members of campaigns the user is in can see preferences
    """
    
    PRIVACY_LEVEL_CHOICES = [
        ('private', 'Private'),
        ('gm_only', 'GM Only'),
        ('campaign_members', 'Campaign Members'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='safety_preferences',
        help_text="The user these safety preferences belong to"
    )
    
    lines = models.JSONField(
        default=list,
        blank=True,
        help_text="Hard boundaries - content that should never appear (JSON list)"
    )
    
    veils = models.JSONField(
        default=list,
        blank=True,
        help_text="Soft boundaries - content that should fade to black (JSON list)"
    )
    
    privacy_level = models.CharField(
        max_length=20,
        choices=PRIVACY_LEVEL_CHOICES,
        default='gm_only',
        help_text="Who can view these safety preferences"
    )
    
    consent_required = models.BooleanField(
        default=True,
        help_text="Whether explicit consent is required before introducing sensitive content"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)  # type: ignore[var-annotated]
    updated_at = models.DateTimeField(auto_now=True)  # type: ignore[var-annotated]
    
    class Meta:
        verbose_name = "User Safety Preferences"
        verbose_name_plural = "User Safety Preferences"
        db_table = "users_safety_preferences"
    
    def __str__(self):
        """Return string representation of safety preferences."""
        return f"Safety preferences for {self.user.username}"
    
    def clean(self):
        """Validate the safety preferences."""
        super().clean()
        
        # Validate privacy_level choice
        if self.privacy_level not in [choice[0] for choice in self.PRIVACY_LEVEL_CHOICES]:
            raise ValidationError({
                'privacy_level': f"'{self.privacy_level}' is not a valid privacy level choice."
            })