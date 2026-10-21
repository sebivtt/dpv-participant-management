"""Mailweg des Tools (#58). Gerüst; die Umsetzung folgt."""

from django.core.mail.backends.base import BaseEmailBackend


class LogOnlyEmailBackend(BaseEmailBackend):
    """Gerüst."""

    def send_messages(self, email_messages) -> int:
        """Gerüst."""
        return 0
