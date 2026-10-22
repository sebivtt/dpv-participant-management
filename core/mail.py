"""Mailweg des Tools, bis der Versand über den DPV-Mailweg kommt (#58, P5).

Mails gehen nirgendwohin, nur ein Hinweis darauf steht im Log. So schreibt weder die
Testumgebung noch ein Rechner in der Entwicklung je aus Versehen an echte Adressen.
"""

import logging

from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class LogOnlyEmailBackend(BaseEmailBackend):
    """Verschickt keine Mail und schreibt nur ins Log, dass eine nicht verschickt wurde.

    Ohne Empfänger, Absender, Betreff und Inhalt: Mails enthalten Personendaten, später auch
    Gesundheitsangaben, und die gehören nie ins Log (DSG-08, Entscheidung zu #6).
    """

    def send_messages(self, email_messages) -> int:
        """Schreibt je Mail eine Zeile ins Log und meldet null verschickte Mails zurück.

        Null, weil keine Mail angekommen ist; so hält das Tool später keine dieser Mails für
        zugestellt, etwa im Postausgang (P5).
        """
        for _ in email_messages:
            logger.info("Mail nicht verschickt (nur Log)")
        return 0
