"""Gemeinsame Einstellungen für alle Tests."""

# pytester führt pytest in einem eigenen Lauf aus; damit lässt sich prüfen, wie sich die
# Prüfeinstellungen tatsächlich auswirken, nicht nur, wie sie eingetragen sind.
# tests.keycloak_fake stellt den nachgestellten Keycloak für die Login-Tests bereit (#5),
# tests.log_capture die abgefangene Ausgabe des Logs (aus tests/test_fehlerprotokoll.py verschoben).
pytest_plugins = ["pytester", "tests.keycloak_fake", "tests.log_capture"]
