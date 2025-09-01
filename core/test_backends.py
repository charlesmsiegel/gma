"""Custom test backends that suppress verbose output."""

import sys
from io import StringIO

from django.core.mail.backends.locmem import EmailBackend as BaseEmailBackend


class QuietEmailBackend(BaseEmailBackend):
    """Email backend that stores emails in memory but suppresses ALL output."""

    def send_messages(self, email_messages):
        """Send messages with complete output suppression."""
        if not email_messages:
            return 0

        # Capture and suppress all output during parent method call
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # Redirect all output to null
            sys.stdout = StringIO()
            sys.stderr = StringIO()

            # Call parent method to properly store emails in outbox
            # This ensures mail.outbox works correctly
            return super().send_messages(email_messages)

        finally:
            # Always restore original streams
            sys.stdout = old_stdout
            sys.stderr = old_stderr
