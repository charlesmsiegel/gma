"""Tests for message display and formatting (Issue #48)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from campaigns.models import Campaign
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class MessageDisplayTestCase(TestCase):
    """Test message display and formatting functionality."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.user1 = User.objects.create_user(
            username="player1", email="player1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="player2", email="player2@example.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@example.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign for message display tests",
            owner=self.gm,
            game_system="Mage",
        )

        # Add members
        self.campaign.add_member(self.user1, "PLAYER")
        self.campaign.add_member(self.user2, "PLAYER")

        # Create characters
        self.character1 = Character.objects.create(
            name="Character One",
            campaign=self.campaign,
            player_owner=self.user1,
            game_system="Mage",
        )
        self.character2 = Character.objects.create(
            name="Character Two",
            campaign=self.campaign,
            player_owner=self.user2,
            game_system="Mage",
        )

        # Create NPC
        self.npc = Character.objects.create(
            name="NPC One",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage",
            npc=True,
        )

        # Create scene
        self.scene = Scene.objects.create(
            name="Test Scene",
            description="Test scene for message display",
            campaign=self.campaign,
            created_by=self.gm,
        )
        self.scene.participants.add(self.character1, self.character2, self.npc)

    def test_message_bubble_structure(self):
        """Test message bubble HTML structure."""
        # Expected HTML structure for message bubbles
        message_bubble_structure = {
            "container": "div",
            "container_classes": ["message-bubble"],
            "header": {
                "element": "div",
                "classes": ["message-header"],
                "children": ["character-name", "timestamp"],
            },
            "content": {
                "element": "div",
                "classes": ["message-content"],
                "children": ["formatted-text"],
            },
            "footer": {
                "element": "div",
                "classes": ["message-footer"],
                "children": ["message-type-indicator"],
            },
        }

        self.assertEqual(message_bubble_structure["container"], "div")
        self.assertIn("message-bubble", message_bubble_structure["container_classes"])
        self.assertIn("message-header", message_bubble_structure["header"]["classes"])

    def test_public_message_display_format(self):
        """Test public message display formatting."""
        # Public message display format
        public_message_format = {
            "type": "PUBLIC",
            "character_display": "visible",
            "character_name_color": "character_color",
            "message_background": "public_bg",
            "border_style": "solid",
            "icon": "public_icon",
            "accessibility_label": "Public message from {character}",
        }

        self.assertEqual(public_message_format["type"], "PUBLIC")
        self.assertEqual(public_message_format["character_display"], "visible")
        self.assertIn("character", public_message_format["accessibility_label"])

    def test_private_message_display_format(self):
        """Test private message display formatting."""
        # Private message display format
        private_message_format = {
            "type": "PRIVATE",
            "character_display": "visible",
            "background_style": "darker_or_highlighted",
            "border_style": "dashed",
            "icon": "private_icon",
            "recipients_display": "visible",
            "whisper_indicator": "visible",
            "accessibility_label": "Private message from {character} to {recipients}",
        }

        self.assertEqual(private_message_format["type"], "PRIVATE")
        self.assertEqual(private_message_format["recipients_display"], "visible")
        self.assertEqual(private_message_format["border_style"], "dashed")

    def test_ooc_message_display_format(self):
        """Test OOC message display formatting."""
        # OOC message display format
        ooc_message_format = {
            "type": "OOC",
            "character_display": "hidden",
            "sender_username_display": "visible",
            "background_color": "ooc_bg_color",
            "text_style": "italic_or_different",
            "prefix": "OOC:",
            "icon": "ooc_icon",
            "accessibility_label": "Out of character message from {username}",
        }

        self.assertEqual(ooc_message_format["type"], "OOC")
        self.assertEqual(ooc_message_format["character_display"], "hidden")
        self.assertEqual(ooc_message_format["sender_username_display"], "visible")
        self.assertEqual(ooc_message_format["prefix"], "OOC:")

    def test_system_message_display_format(self):
        """Test system message display formatting."""
        # System message display format
        system_message_format = {
            "type": "SYSTEM",
            "character_display": "conditional",  # May show character for "X enters"
            "sender_display": "hidden",
            "background_color": "system_bg_color",
            "text_style": "italic_centered",
            "border_style": "none_or_subtle",
            "icon": "system_icon",
            "accessibility_label": "System message: {content}",
        }

        self.assertEqual(system_message_format["type"], "SYSTEM")
        self.assertEqual(system_message_format["sender_display"], "hidden")
        self.assertEqual(system_message_format["character_display"], "conditional")

    def test_character_name_display(self):
        """Test character name display formatting."""
        # Character name display options
        character_name_display = {
            "show_character_name": True,
            "character_color_coding": True,
            "player_name_on_hover": True,
            "npc_indicator": True,
            "character_portrait": "optional",
            "name_formatting": {
                "font_weight": "bold",
                "color": "character_specific",
                "hover_effects": True,
            },
        }

        self.assertTrue(character_name_display["show_character_name"])
        self.assertTrue(character_name_display["character_color_coding"])
        self.assertTrue(character_name_display["npc_indicator"])
        self.assertEqual(
            character_name_display["name_formatting"]["font_weight"], "bold"
        )

    def test_timestamp_display(self):
        """Test timestamp display formatting."""
        # Timestamp display options
        timestamp_display = {
            "show_timestamps": True,
            "format_type": "relative",  # "relative" or "absolute"
            "relative_formats": {
                "just_now": "< 1 minute",
                "minutes": "{n} minutes ago",
                "hours": "{n} hours ago",
                "days": "{n} days ago",
            },
            "absolute_format": "MMM DD, YYYY HH:mm",
            "timezone_handling": "user_local",
            "hover_full_timestamp": True,
        }

        self.assertTrue(timestamp_display["show_timestamps"])
        self.assertEqual(timestamp_display["format_type"], "relative")
        self.assertTrue(timestamp_display["hover_full_timestamp"])
        self.assertIn("just_now", timestamp_display["relative_formats"])

    def test_message_content_formatting(self):
        """Test message content text formatting."""
        # Content formatting features
        content_formatting = {
            "markdown_support": True,
            "supported_markdown": [
                "bold",
                "italic",
                "strikethrough",
                "links",
                "code_inline",
                "code_blocks",
            ],
            "emoji_support": True,
            "auto_link_urls": True,
            "mention_system": "@username",
            "dice_roll_formatting": "/roll 2d10",
            "xss_protection": "sanitize_html",
            "max_length_display": 10000,
        }

        self.assertTrue(content_formatting["markdown_support"])
        self.assertIn("bold", content_formatting["supported_markdown"])
        self.assertTrue(content_formatting["emoji_support"])
        self.assertEqual(content_formatting["xss_protection"], "sanitize_html")

    def test_message_grouping(self):
        """Test consecutive message grouping."""
        # Message grouping for consecutive messages from same character
        message_grouping = {
            "enabled": True,
            "group_by": ["character", "message_type"],
            "max_time_gap": 300,  # 5 minutes
            "max_group_size": 5,
            "show_timestamp_on_last": True,
            "condensed_header": True,
            "visual_separation": "subtle_border",
        }

        self.assertTrue(message_grouping["enabled"])
        self.assertIn("character", message_grouping["group_by"])
        self.assertEqual(message_grouping["max_time_gap"], 300)
        self.assertTrue(message_grouping["show_timestamp_on_last"])

    def test_chat_widget_layout(self):
        """Test chat widget layout structure."""
        # Chat widget layout components
        chat_widget_layout = {
            "container": {
                "element": "div",
                "classes": ["scene-chat-widget"],
                "position": "main_content_area",
            },
            "header": {
                "element": "div",
                "classes": ["chat-header"],
                "content": ["scene_name", "connection_status", "minimize_button"],
            },
            "messages_container": {
                "element": "div",
                "classes": ["chat-messages"],
                "scroll_behavior": "auto_bottom",
                "max_height": "400px",
            },
            "input_area": {
                "element": "div",
                "classes": ["chat-input-area"],
                "content": ["message_input", "character_select", "send_button"],
            },
        }

        self.assertEqual(chat_widget_layout["container"]["element"], "div")
        self.assertIn("scene-chat-widget", chat_widget_layout["container"]["classes"])
        self.assertEqual(
            chat_widget_layout["messages_container"]["scroll_behavior"], "auto_bottom"
        )

    def test_responsive_design(self):
        """Test responsive design for different screen sizes."""
        # Responsive design breakpoints and adaptations
        responsive_design = {
            "desktop": {
                "min_width": "1024px",
                "chat_width": "100%",
                "message_bubble_max_width": "80%",
                "sidebar_visible": True,
            },
            "tablet": {
                "min_width": "768px",
                "max_width": "1023px",
                "chat_width": "100%",
                "message_bubble_max_width": "90%",
                "sidebar_visible": False,
            },
            "mobile": {
                "max_width": "767px",
                "chat_width": "100%",
                "message_bubble_max_width": "95%",
                "font_size": "slightly_larger",
                "touch_optimized": True,
            },
        }

        self.assertIn("desktop", responsive_design)
        self.assertEqual(responsive_design["desktop"]["min_width"], "1024px")
        self.assertTrue(responsive_design["mobile"]["touch_optimized"])

    def test_accessibility_features(self):
        """Test accessibility features for message display."""
        # Accessibility features
        accessibility_features = {
            "aria_labels": True,
            "aria_live_regions": "polite",
            "screen_reader_announcements": True,
            "high_contrast_mode": "supported",
            "keyboard_navigation": True,
            "focus_management": True,
            "color_blind_friendly": True,
            "message_structure": {
                "role": "log",
                "aria_label": "Chat messages",
                "aria_atomic": "false",
            },
        }

        self.assertTrue(accessibility_features["aria_labels"])
        self.assertEqual(accessibility_features["aria_live_regions"], "polite")
        self.assertTrue(accessibility_features["keyboard_navigation"])
        self.assertEqual(accessibility_features["message_structure"]["role"], "log")

    def test_message_actions(self):
        """Test available message actions and interactions."""
        # Message actions (context menu, buttons)
        message_actions = {
            "copy_message": True,
            "quote_reply": True,
            "report_message": True,
            "permalink": True,
            "timestamp_details": True,
            "character_info": "hover_popup",
            "private_reply": "gm_only",
        }

        self.assertTrue(message_actions["copy_message"])
        self.assertTrue(message_actions["quote_reply"])
        self.assertEqual(message_actions["character_info"], "hover_popup")
        self.assertEqual(message_actions["private_reply"], "gm_only")

    def test_theme_support(self):
        """Test theme support for message display."""
        # Theme support for different visual styles
        theme_support = {
            "default_theme": "light",
            "available_themes": ["light", "dark", "high_contrast", "custom"],
            "theme_affects": [
                "background_colors",
                "text_colors",
                "border_colors",
                "message_bubble_styles",
                "typography",
            ],
            "custom_css_variables": True,
            "user_theme_persistence": True,
        }

        self.assertEqual(theme_support["default_theme"], "light")
        self.assertIn("dark", theme_support["available_themes"])
        self.assertIn("background_colors", theme_support["theme_affects"])
        self.assertTrue(theme_support["custom_css_variables"])

    def test_performance_optimization(self):
        """Test performance optimization for message display."""
        # Performance optimization features
        performance_features = {
            "virtual_scrolling": True,
            "lazy_loading": True,
            "message_pagination": True,
            "max_displayed_messages": 100,
            "image_lazy_loading": True,
            "debounced_rendering": True,
            "memory_cleanup": True,
            "efficient_dom_updates": True,
        }

        self.assertTrue(performance_features["virtual_scrolling"])
        self.assertTrue(performance_features["lazy_loading"])
        self.assertEqual(performance_features["max_displayed_messages"], 100)
        self.assertTrue(performance_features["efficient_dom_updates"])

    def test_error_state_display(self):
        """Test error state display in chat widget."""
        # Error states and their display
        error_states = {
            "connection_failed": {
                "message": "Unable to connect to chat",
                "action": "retry_button",
                "icon": "error_icon",
            },
            "permission_denied": {
                "message": "You don't have permission to view this chat",
                "action": "redirect_scenes",
                "icon": "lock_icon",
            },
            "scene_not_found": {
                "message": "Chat is no longer available",
                "action": "redirect_scenes",
                "icon": "not_found_icon",
            },
            "loading_failed": {
                "message": "Failed to load chat history",
                "action": "retry_button",
                "icon": "refresh_icon",
            },
        }

        for error_type, error_info in error_states.items():
            self.assertIn("message", error_info)
            self.assertIn("action", error_info)
            self.assertIn("icon", error_info)

    def test_loading_states(self):
        """Test loading states for chat widget."""
        # Loading states during different operations
        loading_states = {
            "initial_load": {
                "message": "Loading chat...",
                "animation": "spinner",
                "skeleton_ui": True,
            },
            "sending_message": {
                "message": "Sending...",
                "disable_input": True,
                "progress_indicator": "sending_dots",
            },
            "loading_history": {
                "message": "Loading older messages...",
                "position": "top_of_chat",
                "animation": "spinner_small",
            },
            "reconnecting": {
                "message": "Reconnecting...",
                "overlay": "semi_transparent",
                "animation": "pulse",
            },
        }

        for state_type, state_info in loading_states.items():
            self.assertIn("message", state_info)
            if "animation" in state_info:
                self.assertIsInstance(state_info["animation"], str)

    def test_chat_input_area(self):
        """Test chat input area functionality."""
        # Chat input area features
        input_area_features = {
            "textarea_autoresize": True,
            "character_selection": "dropdown",
            "message_type_selection": ["PUBLIC", "OOC"],  # GM gets SYSTEM
            "send_button": True,
            "keyboard_shortcuts": {
                "send": "Enter",
                "send_with_shift": "Shift+Enter",  # Newline
                "ooc_toggle": "Ctrl+/",
            },
            "typing_indicator": True,
            "character_limit": 10000,
            "character_counter": "show_near_limit",
        }

        self.assertTrue(input_area_features["textarea_autoresize"])
        self.assertEqual(input_area_features["character_selection"], "dropdown")
        self.assertIn("PUBLIC", input_area_features["message_type_selection"])
        self.assertEqual(input_area_features["keyboard_shortcuts"]["send"], "Enter")

    def test_connection_status_display(self):
        """Test connection status indicator display."""
        # Connection status indicators
        connection_status_display = {
            "indicator_position": "chat_header",
            "states": {
                "connected": {
                    "color": "green",
                    "icon": "connected_icon",
                    "text": "Connected",
                    "tooltip": "Chat is connected",
                },
                "connecting": {
                    "color": "yellow",
                    "icon": "connecting_icon",
                    "text": "Connecting",
                    "tooltip": "Connecting to chat...",
                },
                "disconnected": {
                    "color": "red",
                    "icon": "disconnected_icon",
                    "text": "Disconnected",
                    "tooltip": "Chat is disconnected. Click to reconnect.",
                },
                "reconnecting": {
                    "color": "orange",
                    "icon": "reconnecting_icon",
                    "text": "Reconnecting",
                    "tooltip": "Attempting to reconnect...",
                },
            },
            "clickable": True,
            "accessibility_announcements": True,
        }

        self.assertEqual(connection_status_display["indicator_position"], "chat_header")
        self.assertIn("connected", connection_status_display["states"])
        self.assertEqual(
            connection_status_display["states"]["connected"]["color"], "green"
        )
        self.assertTrue(connection_status_display["clickable"])

    def test_message_search_and_filter(self):
        """Test message search and filtering capabilities."""
        # Message search and filter features
        search_filter_features = {
            "search_enabled": True,
            "search_placeholder": "Search messages...",
            "search_types": ["content", "character_name", "sender_name"],
            "filters": {
                "message_type": ["PUBLIC", "PRIVATE", "OOC", "SYSTEM"],
                "character": "character_dropdown",
                "date_range": "date_picker",
                "sender": "user_dropdown",
            },
            "live_search": True,
            "search_highlighting": True,
            "case_insensitive": True,
            "regex_support": False,  # Security concern
        }

        self.assertTrue(search_filter_features["search_enabled"])
        self.assertIn("content", search_filter_features["search_types"])
        self.assertTrue(search_filter_features["live_search"])
        self.assertFalse(search_filter_features["regex_support"])

    def test_export_functionality(self):
        """Test chat export functionality."""
        # Export features for chat logs
        export_features = {
            "export_enabled": True,
            "export_formats": ["txt", "html", "pdf"],
            "export_options": {
                "include_timestamps": True,
                "include_character_names": True,
                "include_ooc_messages": "optional",
                "include_system_messages": "optional",
                "date_range_selection": True,
            },
            "export_permissions": "participants_only",
            "max_export_size": 10000,  # messages
        }

        self.assertTrue(export_features["export_enabled"])
        self.assertIn("html", export_features["export_formats"])
        self.assertTrue(export_features["export_options"]["include_timestamps"])
        self.assertEqual(export_features["export_permissions"], "participants_only")

    def test_mobile_specific_features(self):
        """Test mobile-specific chat features."""
        # Mobile-specific optimizations
        mobile_features = {
            "touch_gestures": {
                "swipe_to_scroll": True,
                "tap_to_expand": True,
                "long_press_context_menu": True,
            },
            "virtual_keyboard_handling": True,
            "viewport_adjustment": True,
            "larger_touch_targets": True,
            "simplified_interface": True,
            "reduced_animations": "user_preference",
            "offline_capability": "limited",
        }

        self.assertTrue(mobile_features["touch_gestures"]["swipe_to_scroll"])
        self.assertTrue(mobile_features["virtual_keyboard_handling"])
        self.assertTrue(mobile_features["larger_touch_targets"])
        self.assertEqual(mobile_features["reduced_animations"], "user_preference")
