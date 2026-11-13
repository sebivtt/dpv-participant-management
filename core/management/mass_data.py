"""Massendaten für den Leistungstest am Ende jeder Phase (#104, NFA-05): Zusatz am Befehl `testdata`.

Gerüst; der Inhalt folgt mit #104.
"""

# Wie viele erfundene Probestämme, Gruppen je Stamm und Personen; eine Organisation hat `OUTLIER` direkte Personen.
TROOPS = 40
GROUPS_PER_TROOP = 5
PERSONS = 5000
OUTLIER = 500


def create(association, consent_by) -> dict:
    """Legt die Massendaten im Bund `association` an; Gerüst, legt noch nichts an."""
    return {"units": 0, "accounts": 0, "managed": 0}
