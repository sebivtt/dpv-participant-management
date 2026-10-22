"""Log des Webservers gunicorn ohne Adressen, IP-Adressen und Meldungstexte (#58).

gunicorn schreibt sein eigenes Log, an Djangos Einstellungen vorbei. An zwei Stellen stünden
dort Daten aus der Anfrage: bei einer ungültigen Anfrage die Anfragezeile samt IP-Adresse und
bei einem Fehler im Webserver die echte Adresse mit Parametern, dazu der Meldungstext. Beides
verbietet die Entscheidung zu #6. Diese Klasse ersetzt die beiden Zeilen durch neutrale.
Alles andere, etwa „Booting worker“, bleibt unverändert.
"""

import sys

from gunicorn.glogging import Logger


class SafeLogger(Logger):
    """Log von gunicorn wie gewohnt, nur ohne Daten aus der Anfrage."""

    def warning(self, msg, *args, **kwargs):
        """Ungültige Anfragen stehen nur als kurze Zeile im Log, ohne Anfragezeile und IP-Adresse."""
        if str(msg).startswith("Invalid request from"):
            msg, args = "Ungültige Anfrage (Webserver)", ()
        super().warning(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Fehler im Webserver stehen nur mit ihrer Art im Log, ohne Adresse, Meldungstext und Ablauf.

        Das gilt für alle Fehler von gunicorn, nicht nur für die bei einer Anfrage: Auch Fehler
        beim Start eines Workers laufen hier durch, und deren Meldungstext lässt sich nicht von
        dem einer Anfrage unterscheiden. Die Zeile sagt deshalb nicht, wobei der Fehler entstand.

        Den Ablauf lässt diese Zeile weg, weil gunicorn ihn samt Meldungstext ausgäbe. Solche
        Fehler entstehen außerhalb von Django, dessen eigenes Fehlerprotokoll (core/errors.py)
        Art und Stellen im Code schon festhält; wer einen nachstellen will, tut das lokal mit
        erfundenen Daten.
        """
        error_type = sys.exc_info()[0]
        name = error_type.__name__ if error_type else "unbekannt"
        self.error("Fehler im Webserver: %s", name)
