"""Gemeinsame Einstellungen für alle Tests."""

# pytester führt pytest in einem eigenen Lauf aus; damit lässt sich prüfen, wie sich die
# Prüfeinstellungen tatsächlich auswirken, nicht nur, wie sie eingetragen sind.
pytest_plugins = ["pytester"]
