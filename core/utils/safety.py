"""
Safety utility classes for the Lines & Veils Safety System.

This module provides utility classes for content analysis, privacy control,
warning message generation, audit logging, and theme classification.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from django.utils import timezone

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Utility class for analyzing content for safety concerns."""
    
    # Extended keyword categories for content analysis
    VIOLENCE_KEYWORDS = [
        "attack", "attacks", "attacking", "battle", "blood", "bloodshed", 
        "combat", "death", "die", "dies", "dying", "fight", "fighting", 
        "hit", "hits", "hurt", "kill", "kills", "killing", "murder", 
        "pain", "stab", "sword", "violence", "violent", "war", "weapon", 
        "wound", "wounds", "assault", "harm", "injure", "strike", "shoot",
        "beating", "brutality", "aggression", "torture", "slash", "cut"
    ]
    
    SEXUAL_KEYWORDS = [
        "sexual", "sex", "intimate", "romance", "romantic", "seduction",
        "arousal", "desire", "passion", "adult", "mature", "erotic",
        "sexual content", "sexual violence", "rape", "assault"
    ]
    
    TORTURE_KEYWORDS = [
        "torture", "torturing", "tortured", "torment", "torments",
        "anguish", "agony", "suffering", "graphic torture", "interrogation",
        "brutality", "cruelty", "sadism", "mutilation"
    ]
    
    ANIMAL_HARM_KEYWORDS = [
        "animal harm", "animal abuse", "animal cruelty", "animals harmed",
        "kill animal", "killing animals", "hurt animals", "pet death",
        "animal torture", "animal sacrifice"
    ]
    
    MENTAL_HEALTH_KEYWORDS = [
        "mental health", "mental illness", "depression", "anxiety", "trauma",
        "ptsd", "suicide", "self-harm", "breakdown", "psychosis", "madness",
        "insanity", "psychiatric", "therapy", "counseling", "medication"
    ]
    
    SUPERNATURAL_KEYWORDS = [
        "supernatural", "magic", "occult", "demon", "demons", "spirit",
        "spirits", "ghost", "ghosts", "ritual", "curse", "cursed",
        "paranormal", "mystical", "otherworldly", "cosmic horror"
    ]
    
    DEATH_KEYWORDS = [
        "death", "dead", "die", "dies", "dying", "killed", "murder",
        "funeral", "grave", "cemetery", "corpse", "body", "deceased",
        "mortality", "fatality", "suicide", "execution"
    ]
    
    KEYWORD_CATEGORIES = {
        'violence': VIOLENCE_KEYWORDS,
        'sexual_content': SEXUAL_KEYWORDS,
        'torture': TORTURE_KEYWORDS,
        'animal_harm': ANIMAL_HARM_KEYWORDS,
        'mental_health': MENTAL_HEALTH_KEYWORDS,
        'supernatural': SUPERNATURAL_KEYWORDS,
        'death': DEATH_KEYWORDS,
    }
    
    def find_keyword_matches(self, content: str, keyword_category: str) -> List[str]:
        """
        Find keyword matches in content for a specific category.
        
        Args:
            content: The content to analyze
            keyword_category: The category of keywords to search for
            
        Returns:
            List of matched keywords
        """
        if not content or keyword_category not in self.KEYWORD_CATEGORIES:
            return []
            
        content_lower = content.lower()
        keywords = self.KEYWORD_CATEGORIES[keyword_category]
        matches = []
        
        for keyword in keywords:
            if keyword in content_lower:
                matches.append(keyword)
                
        return matches
    
    def analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """
        Analyze the sentiment and emotional intensity of content.
        
        Args:
            content: The content to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        if not content:
            return {
                'sentiment_score': 0.0,
                'emotional_intensity': 0.0,
                'dominant_emotions': []
            }
        
        # Simple sentiment analysis based on keyword presence
        positive_words = ['happy', 'joy', 'love', 'peaceful', 'calm', 'hope', 'good', 'nice', 'pleasant']
        negative_words = ['death', 'kill', 'torture', 'pain', 'suffer', 'despair', 'horror', 'evil', 'dark', 'disturb']
        intense_words = ['extreme', 'graphic', 'brutal', 'violent', 'horrific', 'terrifying', 'shocking']
        
        content_words = content.lower().split()
        
        positive_count = sum(1 for word in content_words if any(pos in word for pos in positive_words))
        negative_count = sum(1 for word in content_words if any(neg in word for neg in negative_words))
        intense_count = sum(1 for word in content_words if any(intense in word for intense in intense_words))
        
        # Calculate sentiment score (-1.0 to 1.0)
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words > 0:
            sentiment_score = (positive_count - negative_count) / total_sentiment_words
        else:
            sentiment_score = 0.0
            
        # Calculate emotional intensity (0.0 to 1.0)
        total_words = len(content_words)
        if total_words > 0:
            emotional_intensity = min((negative_count + intense_count) / total_words * 5, 1.0)
        else:
            emotional_intensity = 0.0
            
        # Determine dominant emotions
        dominant_emotions = []
        if negative_count > positive_count:
            dominant_emotions.append('negative')
        if intense_count > 0:
            dominant_emotions.append('intense')
        if positive_count > negative_count:
            dominant_emotions.append('positive')
            
        return {
            'sentiment_score': sentiment_score,
            'emotional_intensity': emotional_intensity,
            'dominant_emotions': dominant_emotions
        }


class PrivacyController:
    """Utility class for handling privacy level access control."""
    
    PRIVACY_LEVELS = {
        'private': 0,      # Only the user themselves
        'gm_only': 1,      # GMs and campaign owners
        'campaign_members': 2,  # All campaign members
    }
    
    def can_access_preferences(
        self, 
        privacy_level: str, 
        requester_role: str, 
        is_preferences_owner: bool = False
    ) -> bool:
        """
        Check if a user can access safety preferences based on privacy level.
        
        Args:
            privacy_level: The privacy level of the preferences
            requester_role: The role of the user requesting access
            is_preferences_owner: Whether the requester owns the preferences
            
        Returns:
            True if access is allowed
        """
        # Owner can always access their own preferences
        if is_preferences_owner:
            return True
            
        # Check privacy level permissions
        if privacy_level == 'private':
            return False  # Only owner can access private preferences
            
        elif privacy_level == 'gm_only':
            return requester_role in ['gm', 'owner']
            
        elif privacy_level == 'campaign_members':
            return requester_role in ['gm', 'owner', 'player']
            
        return False
    
    def get_privacy_level_description(self, privacy_level: str) -> str:
        """
        Get a human-readable description of a privacy level.
        
        Args:
            privacy_level: The privacy level
            
        Returns:
            Human-readable description
        """
        descriptions = {
            'private': 'Only visible to you',
            'gm_only': 'Visible to GMs and campaign owners',
            'campaign_members': 'Visible to all campaign members'
        }
        return descriptions.get(privacy_level, 'Unknown privacy level')


class WarningMessageGenerator:
    """Utility class for generating user-friendly warning messages."""
    
    def generate_lines_warning(self, violated_lines: List[str], user_name: str) -> str:
        """
        Generate a warning message for violated lines (hard boundaries).
        
        Args:
            violated_lines: List of violated hard boundaries
            user_name: Name of the user whose boundaries were violated
            
        Returns:
            User-friendly warning message
        """
        if not violated_lines:
            return ""
            
        if len(violated_lines) == 1:
            return (
                f"⚠️ Content Alert: This content may violate {user_name}'s hard boundary "
                f"regarding '{violated_lines[0]}'. Please review and modify the content "
                f"before proceeding."
            )
        else:
            lines_text = "', '".join(violated_lines)
            return (
                f"⚠️ Content Alert: This content may violate {user_name}'s hard boundaries "
                f"regarding '{lines_text}'. Please review and modify the content "
                f"before proceeding."
            )
    
    def generate_veils_warning(self, triggered_veils: List[str], user_name: str) -> str:
        """
        Generate a warning message for triggered veils (fade-to-black content).
        
        Args:
            triggered_veils: List of triggered fade-to-black preferences
            user_name: Name of the user whose preferences were triggered
            
        Returns:
            User-friendly warning message
        """
        if not triggered_veils:
            return ""
            
        if len(triggered_veils) == 1:
            return (
                f"ℹ️ Content Notice: This content involves '{triggered_veils[0]}', "
                f"which {user_name} prefers to fade-to-black. Consider handling "
                f"this content off-screen or with minimal detail."
            )
        else:
            veils_text = "', '".join(triggered_veils)
            return (
                f"ℹ️ Content Notice: This content involves '{veils_text}', "
                f"which {user_name} prefers to fade-to-black. Consider handling "
                f"this content off-screen or with minimal detail."
            )
    
    def generate_consent_required_message(self, user_name: str) -> str:
        """
        Generate a message indicating consent is required.
        
        Args:
            user_name: Name of the user who requires consent
            
        Returns:
            Consent required message
        """
        return (
            f"🤝 Consent Required: {user_name} has requested explicit consent "
            f"before including content that affects their safety preferences. "
            f"Please check with them before proceeding."
        )
    
    def generate_privacy_restricted_message(self, user_name: str) -> str:
        """
        Generate a message for privacy-restricted preferences.
        
        Args:
            user_name: Name of the user whose preferences are private
            
        Returns:
            Privacy restriction message
        """
        return (
            f"🔒 Privacy Notice: {user_name}'s safety preferences are private. "
            f"Please check with them directly about any content concerns."
        )


class SafetyAuditLogger:
    """Utility class for audit logging of safety-related operations."""
    
    def log_safety_check(
        self,
        campaign: Any,
        user: Any,
        content_summary: str,
        validation_result: Dict[str, Any],
        action_taken: str
    ) -> Dict[str, Any]:
        """
        Log a safety validation event.
        
        Args:
            campaign: The campaign object
            user: The user object
            content_summary: Summary of the content that was checked
            validation_result: Result of the safety validation
            action_taken: Action taken based on the validation
            
        Returns:
            Dictionary with log entry data
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'campaign_id': campaign.id if campaign else None,
            'campaign_name': campaign.name if campaign else None,
            'user_id': user.id if user else None,
            'username': user.username if user else None,
            'content_summary': content_summary,
            'validation_result': validation_result,
            'action_taken': action_taken,
            'is_safe': validation_result.get('is_safe', True),
            'lines_violated': validation_result.get('lines_violated', []),
            'veils_triggered': validation_result.get('veils_triggered', []),
            'consent_required': validation_result.get('consent_required', False)
        }
        
        # Log to Django logger
        logger.info(
            f"Safety check: campaign={campaign.id if campaign else 'None'}, "
            f"user={user.username if user else 'None'}, "
            f"safe={log_entry['is_safe']}, action={action_taken}"
        )
        
        return log_entry
    
    def log_preference_update(
        self,
        user: Any,
        old_preferences: Dict[str, Any],
        new_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Log a safety preference update.
        
        Args:
            user: The user whose preferences were updated
            old_preferences: Previous preference values
            new_preferences: New preference values
            
        Returns:
            Dictionary with log entry data
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'user_id': user.id,
            'username': user.username,
            'action': 'preference_update',
            'old_preferences': old_preferences,
            'new_preferences': new_preferences,
            'changes': self._calculate_preference_changes(old_preferences, new_preferences)
        }
        
        logger.info(
            f"Safety preferences updated: user={user.username}, "
            f"changes={list(log_entry['changes'].keys())}"
        )
        
        return log_entry
    
    def _calculate_preference_changes(
        self, 
        old_prefs: Dict[str, Any], 
        new_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate what changed between old and new preferences."""
        changes = {}
        
        for key in ['lines', 'veils', 'privacy_level', 'consent_required']:
            old_value = old_prefs.get(key)
            new_value = new_prefs.get(key)
            
            if old_value != new_value:
                changes[key] = {
                    'old': old_value,
                    'new': new_value
                }
                
        return changes


class SafetyThemeClassifier:
    """Utility class for categorizing and classifying safety themes."""
    
    SEVERITY_CLASSIFICATIONS = {
        'high_severity': [
            'sexual_content', 'sexual violence', 'rape', 'child harm', 
            'animal_harm', 'animal harm', 'animal cruelty', 'graphic torture', 
            'extreme violence', 'suicide', 'self-harm'
        ],
        'medium_severity': [
            'violence', 'death', 'torture', 'mental illness', 
            'substance abuse', 'body horror', 'medical procedures'
        ],
        'low_severity': [
            'supernatural', 'mild violence', 'romantic themes', 
            'historical racism', 'period-appropriate language'
        ]
    }
    
    CONSENT_REQUIRED_THEMES = [
        'sexual_content', 'sexual violence', 'torture', 'graphic torture',
        'animal harm', 'child harm', 'suicide', 'self-harm', 'extreme violence'
    ]
    
    def categorize_themes(self, themes: List[str]) -> Dict[str, List[str]]:
        """
        Categorize a list of themes by severity and consent requirements.
        
        Args:
            themes: List of theme names to categorize
            
        Returns:
            Dictionary with categorized themes
        """
        categorized = {
            'high_severity': [],
            'medium_severity': [],
            'low_severity': [],
            'requires_consent': [],
            'uncategorized': []
        }
        
        for theme in themes:
            theme_lower = theme.lower()
            categorized_theme = False
            
            # Check severity levels
            for severity, theme_list in self.SEVERITY_CLASSIFICATIONS.items():
                if any(self._theme_matches(theme_lower, cat_theme) for cat_theme in theme_list):
                    categorized[severity].append(theme)
                    categorized_theme = True
                    break
            
            # Check consent requirements
            if any(self._theme_matches(theme_lower, consent_theme) for consent_theme in self.CONSENT_REQUIRED_THEMES):
                categorized['requires_consent'].append(theme)
            
            # Track uncategorized themes
            if not categorized_theme:
                categorized['uncategorized'].append(theme)
        
        return categorized
    
    def get_theme_severity(self, theme: str) -> str:
        """
        Get the severity level of a specific theme.
        
        Args:
            theme: The theme to classify
            
        Returns:
            Severity level string
        """
        theme_lower = theme.lower()
        
        for severity, theme_list in self.SEVERITY_CLASSIFICATIONS.items():
            if any(self._theme_matches(theme_lower, cat_theme) for cat_theme in theme_list):
                return severity
                
        return 'uncategorized'
    
    def requires_consent(self, theme: str) -> bool:
        """
        Check if a theme typically requires explicit consent.
        
        Args:
            theme: The theme to check
            
        Returns:
            True if theme typically requires consent
        """
        theme_lower = theme.lower()
        return any(
            self._theme_matches(theme_lower, consent_theme) 
            for consent_theme in self.CONSENT_REQUIRED_THEMES
        )
    
    def get_theme_recommendations(self, themes: List[str]) -> Dict[str, Any]:
        """
        Get recommendations for handling a list of themes.
        
        Args:
            themes: List of themes to analyze
            
        Returns:
            Dictionary with handling recommendations
        """
        categorized = self.categorize_themes(themes)
        
        recommendations = {
            'overall_risk_level': self._calculate_risk_level(categorized),
            'consent_required': len(categorized['requires_consent']) > 0,
            'high_priority_themes': categorized['high_severity'],
            'handling_suggestions': [],
            'discussion_points': []
        }
        
        # Generate handling suggestions
        if categorized['high_severity']:
            recommendations['handling_suggestions'].append(
                "Consider whether high-severity content is necessary for the story"
            )
            recommendations['handling_suggestions'].append(
                "Discuss boundaries with all participants before including this content"
            )
        
        if categorized['requires_consent']:
            recommendations['handling_suggestions'].append(
                "Obtain explicit consent from affected participants"
            )
        
        if categorized['medium_severity']:
            recommendations['handling_suggestions'].append(
                "Consider fade-to-black or off-screen handling for sensitive content"
            )
        
        # Generate discussion points
        if categorized['high_severity'] or categorized['requires_consent']:
            recommendations['discussion_points'].append(
                "Session zero discussion recommended"
            )
        
        return recommendations
    
    def _theme_matches(self, theme1: str, theme2: str) -> bool:
        """Check if two themes match (case-insensitive, partial matching)."""
        return theme1 in theme2.lower() or theme2.lower() in theme1
    
    def _calculate_risk_level(self, categorized: Dict[str, List[str]]) -> str:
        """Calculate overall risk level based on categorized themes."""
        if categorized['high_severity']:
            return 'high'
        elif categorized['medium_severity']:
            return 'medium'
        elif categorized['low_severity']:
            return 'low'
        else:
            return 'minimal'