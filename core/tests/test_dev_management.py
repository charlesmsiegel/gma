"""
Tests for development management commands.
"""

from io import StringIO
from unittest.mock import MagicMock, patch, call

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings

# Import models that exist, handle those that don't exist yet gracefully


class ResetDevDbCommandTest(TransactionTestCase):
    """Test the reset_dev_db management command."""

    def setUp(self):
        """Set up test fixtures."""
        self.stdout = StringIO()
        self.stderr = StringIO()

    @patch('core.management.commands.reset_dev_db.call_command')
    @patch('core.management.commands.reset_dev_db.getpass')
    @patch('builtins.input')
    def test_reset_dev_db_with_confirmation(self, mock_input, mock_getpass, mock_call_command):
        """Test reset_dev_db command with user confirmation."""
        # Mock user confirmation and password input
        mock_input.side_effect = ['yes', 'admin', 'admin@example.com']  # confirmation, username, email
        mock_getpass.return_value = 'password123'  # password
        
        call_command('reset_dev_db', stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('⚠️  WARNING: This will delete ALL data', output)
        self.assertIn('✅ Database reset completed successfully!', output)
        
        # Verify the expected commands were called
        expected_calls = [
            call('flush', '--noinput'),
            call('migrate'),
        ]
        mock_call_command.assert_has_calls(expected_calls, any_order=True)

    @patch('core.management.commands.reset_dev_db.call_command')
    @patch('builtins.input')
    def test_reset_dev_db_without_confirmation(self, mock_input, mock_call_command):
        """Test reset_dev_db command when user cancels."""
        # Mock user cancellation
        mock_input.return_value = 'no'
        
        call_command('reset_dev_db', stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('⚠️  WARNING: This will delete ALL data', output)
        self.assertIn('❌ Operation cancelled', output)
        
        # Verify no database commands were called
        mock_call_command.assert_not_called()

    @patch('core.management.commands.reset_dev_db.call_command')
    @patch('core.management.commands.reset_dev_db.getpass')
    @patch('builtins.input')
    def test_reset_dev_db_force_option(self, mock_input, mock_getpass, mock_call_command):
        """Test reset_dev_db command with --force option (no confirmation)."""
        # Mock superuser creation inputs
        mock_input.side_effect = ['admin', 'admin@example.com']  # username, email
        mock_getpass.return_value = 'password123'  # password
        
        call_command('reset_dev_db', force=True, stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertNotIn('⚠️  WARNING: This will delete ALL data', output)
        self.assertIn('✅ Database reset completed successfully!', output)
        
        # Verify the expected commands were called
        expected_calls = [
            call('flush', '--noinput'),
            call('migrate'),
        ]
        mock_call_command.assert_has_calls(expected_calls, any_order=True)

    @patch('core.management.commands.reset_dev_db.call_command')
    @patch('core.management.commands.reset_dev_db.getpass')
    @patch('builtins.input')
    def test_reset_dev_db_with_superuser_creation(self, mock_input, mock_getpass, mock_call_command):
        """Test reset_dev_db command with superuser creation."""
        # Mock user confirmation and superuser details
        mock_input.side_effect = ['yes', 'admin', 'admin@example.com']  # confirmation, username, email
        mock_getpass.return_value = 'password123'  # password
        
        call_command('reset_dev_db', stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('✅ Database reset completed successfully!', output)
        self.assertIn('Creating superuser account...', output)

    @patch('core.management.commands.reset_dev_db.call_command')
    def test_reset_dev_db_no_superuser_option(self, mock_call_command):
        """Test reset_dev_db command with --no-superuser option."""
        call_command('reset_dev_db', force=True, no_superuser=True, stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('✅ Database reset completed successfully!', output)
        self.assertNotIn('Creating superuser account...', output)

    @patch('core.management.commands.reset_dev_db.call_command')
    @patch('core.management.commands.reset_dev_db.getpass')
    @patch('builtins.input')
    def test_reset_dev_db_handles_flush_error(self, mock_input, mock_getpass, mock_call_command):
        """Test reset_dev_db command handles database flush errors."""
        # Mock superuser creation inputs (though they won't be reached)
        mock_input.side_effect = ['admin', 'admin@example.com']  # username, email
        mock_getpass.return_value = 'password123'  # password
        
        # Mock flush command to raise an exception
        mock_call_command.side_effect = [
            Exception('Database connection error'),
            None,  # migrate command succeeds
        ]
        
        with self.assertRaises(SystemExit) as cm:
            call_command('reset_dev_db', force=True, stdout=self.stdout, stderr=self.stderr)
        
        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn('❌ Failed to flush database', output)
        self.assertIn('Database connection error', output)

    @patch('core.management.commands.reset_dev_db.call_command')
    @patch('core.management.commands.reset_dev_db.getpass')
    @patch('builtins.input')
    def test_reset_dev_db_handles_migrate_error(self, mock_input, mock_getpass, mock_call_command):
        """Test reset_dev_db command handles migration errors."""
        # Mock superuser creation inputs (though they won't be reached)
        mock_input.side_effect = ['admin', 'admin@example.com']  # username, email
        mock_getpass.return_value = 'password123'  # password
        
        # Mock migrate command to raise an exception
        mock_call_command.side_effect = [
            None,  # flush command succeeds
            Exception('Migration error'),
        ]
        
        with self.assertRaises(SystemExit) as cm:
            call_command('reset_dev_db', force=True, stdout=self.stdout, stderr=self.stderr)
        
        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn('❌ Failed to run migrations', output)
        self.assertIn('Migration error', output)


class CreateTestDataCommandTest(TestCase):
    """Test the create_test_data management command."""

    def setUp(self):
        """Set up test fixtures."""
        self.stdout = StringIO()
        self.stderr = StringIO()

    def test_create_test_data_default(self):
        """Test create_test_data command with default settings."""
        call_command('create_test_data', stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('Creating test data...', output)
        self.assertIn('✅ Test data created successfully!', output)
        
        # Verify test data was created
        self.assertTrue(User.objects.filter(username='testuser').exists())
        self.assertTrue(User.objects.filter(username='gm_user').exists())
        
        # Test campaign creation if models are available
        try:
            from campaigns.models import Campaign
            self.assertTrue(Campaign.objects.filter(name='Test Campaign').exists())
        except (ImportError, AttributeError):
            # Campaign model not implemented yet, skip this check
            pass
        
        # Test character creation if models are available
        try:
            from characters.models import Character
            self.assertTrue(Character.objects.count() > 0)
        except (ImportError, AttributeError):
            # Character model not implemented yet, skip this check
            pass

    def test_create_test_data_custom_counts(self):
        """Test create_test_data command with custom counts."""
        call_command(
            'create_test_data',
            users=3,
            campaigns=2,
            characters=5,
            stdout=self.stdout,
            stderr=self.stderr
        )
        
        output = self.stdout.getvalue()
        self.assertIn('Creating test data...', output)
        self.assertIn('✅ Test data created successfully!', output)
        
        # Verify correct counts (including the specific test users)
        self.assertEqual(User.objects.count(), 5)  # 3 custom + testuser + gm_user
        
        # Test campaign counts if models are available
        try:
            from campaigns.models import Campaign
            self.assertEqual(Campaign.objects.count(), 3)  # 2 custom + Test Campaign
        except (ImportError, AttributeError):
            # Campaign model not implemented yet, skip this check
            pass
        
        # Test character counts if models are available
        try:
            from characters.models import Character
            self.assertEqual(Character.objects.count(), 5)
        except (ImportError, AttributeError):
            # Character model not implemented yet, skip this check
            pass

    def test_create_test_data_clear_option(self):
        """Test create_test_data command with --clear option."""
        # Create some initial data
        User.objects.create_user('existing_user', 'existing@example.com', 'password')
        
        call_command('create_test_data', clear=True, stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('Clearing existing test data...', output)
        self.assertIn('✅ Test data created successfully!', output)
        
        # Verify old data was cleared and new data created
        self.assertFalse(User.objects.filter(username='existing_user').exists())
        self.assertTrue(User.objects.filter(username='testuser').exists())

    @patch('django.contrib.auth.models.User.objects.create_user')
    def test_create_test_data_handles_user_creation_error(self, mock_create_user):
        """Test create_test_data command handles user creation errors."""
        mock_create_user.side_effect = Exception('User creation failed')
        
        with self.assertRaises(SystemExit) as cm:
            call_command('create_test_data', stdout=self.stdout, stderr=self.stderr)
        
        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn('❌ Failed to create test data', output)
        self.assertIn('User creation failed', output)

    def test_create_test_data_dry_run_option(self):
        """Test create_test_data command with --dry-run option."""
        call_command('create_test_data', dry_run=True, stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('DRY RUN: Would create test data', output)
        self.assertIn('✅ Dry run completed!', output)
        
        # Verify no actual data was created
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_create_test_data_verbose_output(self):
        """Test create_test_data command with verbose output."""
        call_command('create_test_data', verbosity=2, stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('Creating test users...', output)
        self.assertIn('Creating test campaigns...', output)
        self.assertIn('Creating test characters...', output)
        self.assertIn('Created user:', output)
        
        # Only check for campaign/character creation if models exist
        try:
            from campaigns.models import Campaign
            self.assertIn('Created campaign:', output)
        except (ImportError, AttributeError):
            self.assertIn('Campaign model not implemented yet, skipping...', output)
            
        try:
            from characters.models import Character
            self.assertIn('Created character:', output)
        except (ImportError, AttributeError):
            self.assertIn('Character model not implemented yet, skipping...', output)

    def test_create_test_data_zero_counts(self):
        """Test create_test_data command with zero counts."""
        call_command(
            'create_test_data',
            users=0,
            campaigns=0,
            characters=0,
            stdout=self.stdout,
            stderr=self.stderr
        )
        
        output = self.stdout.getvalue()
        self.assertIn('Creating test data...', output)
        self.assertIn('✅ Test data created successfully!', output)
        
        # Only the default testuser and gm_user should be created
        self.assertEqual(User.objects.count(), 2)
        
        # Test campaign counts if models are available
        try:
            from campaigns.models import Campaign
            self.assertEqual(Campaign.objects.count(), 1)  # Just Test Campaign
        except (ImportError, AttributeError):
            # Campaign model not implemented yet, skip this check
            pass
        
        # Test character counts if models are available
        try:
            from characters.models import Character
            self.assertEqual(Character.objects.count(), 0)
        except (ImportError, AttributeError):
            # Character model not implemented yet, skip this check
            pass

    def test_create_test_data_handles_missing_models(self):
        """Test create_test_data command gracefully handles missing models."""
        # This test verifies that the command works even when Campaign/Character models don't exist
        call_command('create_test_data', verbosity=2, stdout=self.stdout, stderr=self.stderr)
        
        output = self.stdout.getvalue()
        self.assertIn('Creating test data...', output)
        self.assertIn('✅ Test data created successfully!', output)
        
        # Users should always be created (using Django's built-in User model)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        self.assertTrue(User.objects.filter(username='gm_user').exists())
        
        # Check that appropriate messages are shown for missing models
        try:
            from campaigns.models import Campaign
        except (ImportError, AttributeError):
            self.assertIn('Campaign model not implemented yet, skipping...', output)
            
        try:
            from characters.models import Character
        except (ImportError, AttributeError):
            self.assertIn('Character model not implemented yet, skipping...', output)