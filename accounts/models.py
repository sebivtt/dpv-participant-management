"""Datenmodell der Konten."""

from django.contrib.auth.models import AbstractUser
from django.db import DatabaseError, models, transaction

from access.keys import key_field

# Höchstens 50 Zeichen, nach dem Entfernen der Leerzeichen am Rand (#111).
SCOUT_NAME_MAX_LENGTH = 50


class User(AbstractUser):
    """Konto einer Person im Tool.

    Verknüpft ist es mit genau einem Keycloak-Konto über dessen feste Kennung (`sub`), die
    allauth als SocialAccount.uid speichert, nie über Benutzername oder Mail (#5). Name
    und Mail kommen bei jedem Login neu aus Keycloak. Ein eigenes Modell statt Djangos
    Standard, weil ein späterer Wechsel aufwendig ist. Zusätzlich hat es die zufällige
    Kennung für Adressen (#64), die beim ersten Login entsteht, und den Fahrtennamen (#111),
    den nur die Person selbst auf „Mein Profil“ einträgt; Keycloak liefert ihn nicht.
    """

    key = key_field()
    scout_name = models.CharField(max_length=SCOUT_NAME_MAX_LENGTH, blank=True, default="")

    @property
    def short_name(self) -> str:
        """Der Name in Begrüßung und Profilkreis, leer, wenn er fehlt (#77, #111).

        Beide fragen nur hier. Mit Fahrtenname ist es der Fahrtenname, sonst der Vorname;
        Leerzeichen am Rand entfernen schon der Login (`accounts/adapter.py`) und das
        Formular (`accounts/forms.py`), ein Name nur aus Leerzeichen ist hier also leer.
        """
        return self.scout_name or self.first_name

    @property
    def display_name(self) -> str:
        """Der volle Name, z. B. „Kiwi (Erika Testfrau)“; Regel in `display_name()` unten."""
        return display_name(self.first_name, self.last_name, self.scout_name)

    def set_scout_name(self, value: str) -> None:
        """Speichert den Fahrtennamen und nur ihn (EP-03).

        Nur dieses eine Feld wird geschrieben, damit ein zweiter Tab mit altem Stand nichts
        anderes überschreibt, etwa Name oder Mail vom letzten Login. Scheitert das Speichern,
        behält das Objekt den alten Wert, damit die Seite danach nicht den ungespeicherten zeigt.
        """
        previous = self.scout_name
        self.scout_name = value
        try:
            # Eigener Sicherungspunkt: Nach einem Fehler kann die Anfrage die Seite noch lesen.
            with transaction.atomic():
                self.save(update_fields=["scout_name"])
        except DatabaseError:
            self.scout_name = previous
            raise


def display_name(first_name: str, last_name: str, scout_name: str) -> str:
    """Der volle Name einer Person, wie ihn jede Seite zeigt: „Kiwi (Erika Testfrau)“ (#111).

    Die gemeinsame Stelle für „Mein Profil“ und später Listen und Suche (#93, #94, #65, #117;
    Nachklärung vom 26.10.2026). Ohne Fahrtenname „Erika Testfrau“; ohne Vor- und Nachname
    nur „Kiwi“, ohne leere Klammern. Fehlt alles, ist das Ergebnis leer, und die Seite
    entscheidet, was sie stattdessen zeigt (auf „Mein Profil“ den Benutzernamen).
    """
    full_name = " ".join(part for part in (first_name, last_name) if part)
    if scout_name and full_name:
        return f"{scout_name} ({full_name})"
    return scout_name or full_name


class AccountSearch(models.Model):
    """Eine Suche über die genaue Mail oder den Benutzernamen, nur für das Suchlimit (PK-24, #190).

    Gespeichert sind nur, wer gesucht hat und wann, nie wonach: Der Suchbegriff wäre eine Mail
    oder ein Benutzername, also eine Personenangabe über eine andere Person. Was älter als die
    Zeitspanne des Limits ist, löscht die nächste Suche derselben Person; das Protokoll der
    Kontosuchen kommt getrennt mit #144. Vorschläge beim Tippen stehen hier nicht.
    """

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    searched_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["user", "searched_at"])]
