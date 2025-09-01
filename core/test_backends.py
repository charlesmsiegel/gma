"""Custom test backends that suppress verbose output."""

import sys
from io import StringIO

from django.core.mail.backends.locmem import EmailBackend as BaseEmailBackend


class QuietEmailBackend(BaseEmailBackend):
    """Email backend that stores emails in memory but suppresses printing."""

    def send_messages(self, email_messages):
        """Send messages while suppressing any print output."""
        # Temporarily redirect stdout to suppress any printing
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # Call the parent method which handles the actual sending and storage
            result = super().send_messages(email_messages)
        finally:
            # Always restore stdout
            sys.stdout = old_stdout

        return result
