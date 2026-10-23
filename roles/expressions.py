"""Datenbank-Ausdrücke für die Rollen, eigene Datei, damit Migrationen sie ohne das Datenmodell laden."""

from django.db import models


class TransactionStart(models.Func):
    """Beginn der äußersten laufenden Transaktion.

    Djangos `Now()` nimmt in PostgreSQL den Beginn jeder einzelnen Anweisung. So trügen
    „entfernt“ und „vergeben“ eines Wechsels verschiedene Uhrzeiten (#91).
    """

    template = "CURRENT_TIMESTAMP"
    output_field = models.DateTimeField()
