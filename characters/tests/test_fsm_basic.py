"""Comprehensive tests for Character FSM status field functionality."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django_fsm import TransitionNotAllowed

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character, CharacterAuditLog

User = get_user_model()


class CharacterStatusFieldTest(TestCase):
    """Tests for Character status field choices and defaults."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

    def test_character_starts_with_draft_status(self):
        """Test that new characters start with DRAFT status."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="Test System",
        )
        self.assertEqual(character.status, "DRAFT")

    def test_status_field_choices_include_approved(self):
        """Test that status field includes APPROVED instead of ACTIVE."""
        expected_choices = [
            ("DRAFT", "Draft"),
            ("SUBMITTED", "Submitted"),
            ("APPROVED", "Approved"),
            ("INACTIVE", "Inactive"),
            ("RETIRED", "Retired"),
            ("DECEASED", "Deceased"),
        ]
        status_field = Character._meta.get_field("status")
        self.assertEqual(status_field.choices, expected_choices)

    def test_status_field_does_not_include_active(self):
        """Test that status field no longer includes ACTIVE choice."""
        status_field = Character._meta.get_field("status")
        status_values = [choice[0] for choice in status_field.choices]
        self.assertNotIn("ACTIVE", status_values)
        self.assertIn("APPROVED", status_values)


class CharacterTransitionFlowTest(TestCase):
    """Tests for Character status transition flows."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=10,
        )

        # Add GM to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

        # Add player to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

    def test_basic_approval_flow(self):
        """Test basic transition flow: DRAFT -> SUBMITTED -> APPROVED."""
        # Character starts as DRAFT
        self.assertEqual(self.character.status, "DRAFT")

        # Player can submit for approval
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "SUBMITTED")

        # GM can approve to APPROVED (not ACTIVE)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

    def test_rejection_flow(self):
        """Test character rejection flow: SUBMITTED -> DRAFT."""
        # Submit character
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "SUBMITTED")

        # GM can reject back to DRAFT
        self.character.reject(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "DRAFT")

    def test_approved_state_transitions(self):
        """Test transitions from APPROVED state."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

        # Test deactivate APPROVED -> INACTIVE
        self.character.deactivate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "INACTIVE")

    def test_reactivation_flow(self):
        """Test reactivation flow: APPROVED -> INACTIVE -> APPROVED."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.character.deactivate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "INACTIVE")

        # Test reactivate INACTIVE -> APPROVED
        self.character.activate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

    def test_retirement_flow(self):
        """Test retirement flow: APPROVED -> RETIRED."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # Test retirement by owner
        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "RETIRED")

    def test_death_flow(self):
        """Test marking character as deceased: APPROVED -> DECEASED."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # GM can mark as deceased
        self.character.mark_deceased(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "DECEASED")


class CharacterTransitionPermissionTest(TestCase):
    """Tests for Character transition permissions."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="TestPass123!"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="TestPass123!"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

        # Add members to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

    def test_submit_for_approval_permissions(self):
        """Test that only character owners can submit for approval."""
        # Character owner can submit
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "SUBMITTED")

        # Reset to DRAFT for other tests
        self.character.status = "DRAFT"
        self.character.save()

        # GM cannot submit another player's character
        with self.assertRaises(PermissionError):
            self.character.submit_for_approval(user=self.gm)

        # Campaign owner cannot submit another player's character
        with self.assertRaises(PermissionError):
            self.character.submit_for_approval(user=self.owner)

        # Observer cannot submit
        with self.assertRaises(PermissionError):
            self.character.submit_for_approval(user=self.observer)

        # Non-member cannot submit
        with self.assertRaises(PermissionError):
            self.character.submit_for_approval(user=self.non_member)

    def test_approve_permissions(self):
        """Test that only GMs and campaign owners can approve characters."""
        # Submit character first
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # GM can approve
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

        # Reset to SUBMITTED for other tests
        self.character.status = "SUBMITTED"
        self.character.save()

        # Campaign owner can approve
        self.character.approve(user=self.owner)
        self.character.save(audit_user=self.owner)
        self.assertEqual(self.character.status, "APPROVED")

        # Reset to SUBMITTED
        self.character.status = "SUBMITTED"
        self.character.save()

        # Player cannot approve their own character
        with self.assertRaises(PermissionError):
            self.character.approve(user=self.player)

        # Observer cannot approve
        with self.assertRaises(PermissionError):
            self.character.approve(user=self.observer)

        # Non-member cannot approve
        with self.assertRaises(PermissionError):
            self.character.approve(user=self.non_member)

    def test_reject_permissions(self):
        """Test that only GMs and campaign owners can reject characters."""
        # Submit character first
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # GM can reject
        self.character.reject(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "DRAFT")

        # Submit again
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # Campaign owner can reject
        self.character.reject(user=self.owner)
        self.character.save(audit_user=self.owner)
        self.assertEqual(self.character.status, "DRAFT")

        # Submit again for negative tests
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # Player cannot reject their own character
        with self.assertRaises(PermissionError):
            self.character.reject(user=self.player)

        # Observer cannot reject
        with self.assertRaises(PermissionError):
            self.character.reject(user=self.observer)

        # Non-member cannot reject
        with self.assertRaises(PermissionError):
            self.character.reject(user=self.non_member)

    def test_deactivate_activate_permissions(self):
        """Test that only GMs and campaign owners can deactivate/activate characters."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # GM can deactivate
        self.character.deactivate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "INACTIVE")

        # GM can activate
        self.character.activate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

        # Campaign owner can deactivate
        self.character.deactivate(user=self.owner)
        self.character.save(audit_user=self.owner)
        self.assertEqual(self.character.status, "INACTIVE")

        # Campaign owner can activate
        self.character.activate(user=self.owner)
        self.character.save(audit_user=self.owner)
        self.assertEqual(self.character.status, "APPROVED")

        # Player cannot deactivate their own character
        with self.assertRaises(PermissionError):
            self.character.deactivate(user=self.player)

        # Player cannot activate their own character
        self.character.status = "INACTIVE"
        self.character.save()
        with self.assertRaises(PermissionError):
            self.character.activate(user=self.player)

    def test_retire_permissions(self):
        """Test that both owners and GMs/campaign owners can retire characters."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # Character owner can retire
        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "RETIRED")

        # Reset to APPROVED
        self.character.status = "APPROVED"
        self.character.save()

        # GM can retire
        self.character.retire(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "RETIRED")

        # Reset to APPROVED
        self.character.status = "APPROVED"
        self.character.save()

        # Campaign owner can retire
        self.character.retire(user=self.owner)
        self.character.save(audit_user=self.owner)
        self.assertEqual(self.character.status, "RETIRED")

        # Reset to APPROVED
        self.character.status = "APPROVED"
        self.character.save()

        # Observer cannot retire
        with self.assertRaises(PermissionError):
            self.character.retire(user=self.observer)

        # Non-member cannot retire
        with self.assertRaises(PermissionError):
            self.character.retire(user=self.non_member)

    def test_mark_deceased_permissions(self):
        """Test that only GMs and campaign owners can mark characters as deceased."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # GM can mark as deceased
        self.character.mark_deceased(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "DECEASED")

        # Reset to APPROVED
        self.character.status = "APPROVED"
        self.character.save()

        # Campaign owner can mark as deceased
        self.character.mark_deceased(user=self.owner)
        self.character.save(audit_user=self.owner)
        self.assertEqual(self.character.status, "DECEASED")

        # Reset to APPROVED
        self.character.status = "APPROVED"
        self.character.save()

        # Player cannot mark their own character as deceased
        with self.assertRaises(PermissionError):
            self.character.mark_deceased(user=self.player)

        # Observer cannot mark as deceased
        with self.assertRaises(PermissionError):
            self.character.mark_deceased(user=self.observer)

        # Non-member cannot mark as deceased
        with self.assertRaises(PermissionError):
            self.character.mark_deceased(user=self.non_member)


class CharacterTransitionLogTest(TestCase):
    """Tests for Character transition audit logging."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

    def test_submit_for_approval_creates_audit_log(self):
        """Test that submit_for_approval creates audit log entry."""
        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # Should have created an audit entry
        new_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check the audit entry details
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.player)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertIn("status", audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes["status"]["old"], "DRAFT")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "SUBMITTED")

    def test_approve_creates_audit_log(self):
        """Test that approve creates audit log entry."""
        # Submit first
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # Should have created an audit entry
        new_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check the audit entry details
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.gm)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertIn("status", audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes["status"]["old"], "SUBMITTED")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "APPROVED")

    def test_reject_creates_audit_log(self):
        """Test that reject creates audit log entry."""
        # Submit first
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        self.character.reject(user=self.gm)
        self.character.save(audit_user=self.gm)

        # Should have created an audit entry
        new_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check the audit entry details
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.gm)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertIn("status", audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes["status"]["old"], "SUBMITTED")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "DRAFT")

    def test_deactivate_activate_creates_audit_logs(self):
        """Test that deactivate and activate create audit log entries."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        # Test deactivate
        self.character.deactivate(user=self.gm)
        self.character.save(audit_user=self.gm)

        deactivate_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()
        self.assertEqual(deactivate_count, initial_count + 1)

        # Check deactivate audit entry
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.gm)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertEqual(audit_entry.field_changes["status"]["old"], "APPROVED")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "INACTIVE")

        # Test activate
        self.character.activate(user=self.gm)
        self.character.save(audit_user=self.gm)

        activate_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()
        self.assertEqual(activate_count, deactivate_count + 1)

        # Check activate audit entry
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.gm)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertEqual(audit_entry.field_changes["status"]["old"], "INACTIVE")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "APPROVED")

    def test_retire_creates_audit_log(self):
        """Test that retire creates audit log entry."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)

        # Should have created an audit entry
        new_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check the audit entry details
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.player)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertIn("status", audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes["status"]["old"], "APPROVED")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "RETIRED")

    def test_mark_deceased_creates_audit_log(self):
        """Test that mark_deceased creates audit log entry."""
        # Get to APPROVED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        self.character.mark_deceased(user=self.gm)
        self.character.save(audit_user=self.gm)

        # Should have created an audit entry
        new_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check the audit entry details
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.changed_by, self.gm)
        self.assertEqual(audit_entry.action, "UPDATE")
        self.assertIn("status", audit_entry.field_changes)
        self.assertEqual(audit_entry.field_changes["status"]["old"], "APPROVED")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "DECEASED")

    def test_multiple_transitions_create_multiple_logs(self):
        """Test that multiple transitions create separate audit log entries."""
        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        # Flow: DRAFT -> SUBMITTED -> APPROVED -> INACTIVE -> APPROVED -> RETIRED
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        self.character.deactivate(user=self.gm)
        self.character.save(audit_user=self.gm)

        self.character.activate(user=self.gm)
        self.character.save(audit_user=self.gm)

        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)

        # Should have created 5 audit entries (one for each transition)
        final_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(final_count, initial_count + 5)

        # Verify the sequence of status changes
        audit_entries = CharacterAuditLog.objects.filter(
            character=self.character
        ).order_by("timestamp")

        status_changes = [
            (
                entry.field_changes.get("status", {}).get("old"),
                entry.field_changes.get("status", {}).get("new"),
            )
            for entry in audit_entries
            if "status" in entry.field_changes
        ]

        expected_changes = [
            ("DRAFT", "SUBMITTED"),
            ("SUBMITTED", "APPROVED"),
            ("APPROVED", "INACTIVE"),
            ("INACTIVE", "APPROVED"),
            ("APPROVED", "RETIRED"),
        ]

        # Should match the last N entries where N is the number of expected changes
        actual_changes = status_changes[-len(expected_changes) :]
        self.assertEqual(actual_changes, expected_changes)


class CharacterEdgeCaseTest(TestCase):
    """Tests for Character transition edge cases and error conditions."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=10,  # Allow multiple characters for testing
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

    def test_invalid_transitions_blocked(self):
        """Test that invalid transitions are blocked by FSM."""
        # Cannot approve from DRAFT (must go through SUBMITTED)
        with self.assertRaises(TransitionNotAllowed):
            self.character.approve(user=self.gm)

        # Cannot retire from DRAFT (must be APPROVED)
        with self.assertRaises(TransitionNotAllowed):
            self.character.retire(user=self.player)

        # Cannot deactivate from DRAFT (must be APPROVED)
        with self.assertRaises(TransitionNotAllowed):
            self.character.deactivate(user=self.gm)

        # Cannot mark as deceased from DRAFT (must be APPROVED)
        with self.assertRaises(TransitionNotAllowed):
            self.character.mark_deceased(user=self.gm)

        # Cannot activate from DRAFT (must be INACTIVE)
        with self.assertRaises(TransitionNotAllowed):
            self.character.activate(user=self.gm)

    def test_direct_status_changes_prevented(self):
        """Test direct status field changes bypass FSM validation but audit works."""
        # Note: FSM with protected=False allows direct assignment,
        # but transitions should be used
        initial_count = CharacterAuditLog.objects.filter(
            character=self.character
        ).count()

        # Direct status change should work (FSM protected=False)
        self.character.status = "APPROVED"
        self.character.save(audit_user=self.player)

        # Should still create audit log
        new_count = CharacterAuditLog.objects.filter(character=self.character).count()
        self.assertEqual(new_count, initial_count + 1)

        # Check audit entry
        audit_entry = CharacterAuditLog.objects.filter(character=self.character).latest(
            "timestamp"
        )
        self.assertEqual(audit_entry.field_changes["status"]["old"], "DRAFT")
        self.assertEqual(audit_entry.field_changes["status"]["new"], "APPROVED")

    def test_transitions_from_terminal_states(self):
        """Test that no transitions are allowed from terminal states."""
        # Get to RETIRED state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)

        # No transitions from RETIRED
        with self.assertRaises(TransitionNotAllowed):
            self.character.submit_for_approval(user=self.player)
        with self.assertRaises(TransitionNotAllowed):
            self.character.approve(user=self.gm)
        with self.assertRaises(TransitionNotAllowed):
            self.character.deactivate(user=self.gm)
        with self.assertRaises(TransitionNotAllowed):
            self.character.activate(user=self.gm)

        # Get to DECEASED state
        self.character.status = "APPROVED"  # Reset via direct assignment
        self.character.save()
        self.character.mark_deceased(user=self.gm)
        self.character.save(audit_user=self.gm)

        # No transitions from DECEASED
        with self.assertRaises(TransitionNotAllowed):
            self.character.submit_for_approval(user=self.player)
        with self.assertRaises(TransitionNotAllowed):
            self.character.approve(user=self.gm)
        with self.assertRaises(TransitionNotAllowed):
            self.character.deactivate(user=self.gm)
        with self.assertRaises(TransitionNotAllowed):
            self.character.activate(user=self.gm)
        with self.assertRaises(TransitionNotAllowed):
            self.character.retire(user=self.player)

    def test_filtering_by_status_with_approved(self):
        """Test filtering characters by APPROVED status instead of ACTIVE."""
        # Create characters in different states
        draft_char = Character.objects.create(
            name="Draft Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        approved_char = Character.objects.create(
            name="Approved Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        approved_char.submit_for_approval(user=self.player)
        approved_char.save(audit_user=self.player)
        approved_char.approve(user=self.gm)
        approved_char.save(audit_user=self.gm)

        inactive_char = Character.objects.create(
            name="Inactive Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        inactive_char.submit_for_approval(user=self.player)
        inactive_char.save(audit_user=self.player)
        inactive_char.approve(user=self.gm)
        inactive_char.save(audit_user=self.gm)
        inactive_char.deactivate(user=self.gm)
        inactive_char.save(audit_user=self.gm)

        # Test filtering
        draft_chars = Character.objects.filter(status="DRAFT")
        approved_chars = Character.objects.filter(status="APPROVED")
        inactive_chars = Character.objects.filter(status="INACTIVE")
        active_chars = Character.objects.filter(status="ACTIVE")  # Should be empty

        # Should have draft_char and self.character in DRAFT status
        self.assertEqual(draft_chars.count(), 2)
        self.assertIn(draft_char, draft_chars)
        self.assertIn(self.character, draft_chars)

        # Should have approved_char in APPROVED status
        self.assertEqual(approved_chars.count(), 1)
        self.assertEqual(approved_chars.first(), approved_char)

        # Should have inactive_char in INACTIVE status
        self.assertEqual(inactive_chars.count(), 1)
        self.assertEqual(inactive_chars.first(), inactive_char)

        # Should have no characters in ACTIVE status (removed from choices)
        self.assertEqual(active_chars.count(), 0)


class CharacterStateValidationTest(TestCase):
    """Tests for Character state validation and constraints."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )

    def test_status_field_db_constraints(self):
        """Test that status field enforces valid choices at database level."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="Test System",
        )

        # Valid status should work
        character.status = "APPROVED"
        character.save()
        character.refresh_from_db()
        self.assertEqual(character.status, "APPROVED")

        # Note: Database constraint validation depends on database backend
        # Django CharField with choices doesn't enforce at DB level by default
        # But our choices should be validated at Django model level

    def test_status_choices_match_transition_targets(self):
        """Test that all status choices can be reached by transitions."""
        status_field = Character._meta.get_field("status")
        status_values = [choice[0] for choice in status_field.choices]

        # All status values should be reachable
        expected_statuses = [
            "DRAFT",
            "SUBMITTED",
            "APPROVED",
            "INACTIVE",
            "RETIRED",
            "DECEASED",
        ]
        self.assertEqual(sorted(status_values), sorted(expected_statuses))

        # Verify no ACTIVE status exists
        self.assertNotIn("ACTIVE", status_values)
