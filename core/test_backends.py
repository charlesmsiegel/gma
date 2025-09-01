"""Custom test backends that suppress verbose output."""

import sys

from django.core.mail.backends.locmem import EmailBackend as BaseEmailBackend


class QuietEmailBackend(BaseEmailBackend):
    """Email backend that stores emails in memory but suppresses printing."""

    def send_messages(self, email_messages):
        """Send messages with complete output suppression."""
        if not email_messages:
            return 0

        # Suppress all possible output during email processing
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            # Completely suppress output
            sys.stdout = open("/dev/null", "w")
            sys.stderr = open("/dev/null", "w")

            # Store messages in memory without any display
            num_sent = 0
            for message in email_messages:
                # Silently store the message
                self.outbox.append(message)
                num_sent += 1

            return num_sent
        except Exception:
            # If anything fails, still return 0 without output
            return 0
        finally:
            # Always restore streams
            if old_stdout:
                sys.stdout.close() if sys.stdout != old_stdout else None
                sys.stdout = old_stdout
            if old_stderr:
                sys.stderr.close() if sys.stderr != old_stderr else None
                sys.stderr = old_stderr
