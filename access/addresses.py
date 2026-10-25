"""Markierungen für jede Adresse des Tools; der Rundumtest wird rot, wenn eine fehlt (#90).

Jede Seite trägt genau eine der beiden Markierungen:

- `@checks_rights("PK-01", …)`: Die Seite zeigt oder ändert Personen- oder Anmeldedaten und
  fragt dafür die zentrale Rechteprüfung (`request.rights`). Die Kennungen nennen die Zeilen der
  Rechtematrix, die sie umsetzt; der Rundumtest prüft, dass es sie gibt.
- `@without_personal_data("…")`: Die Seite enthält keine Personendaten; die Begründung sagt,
  warum. Die Markierung ist eine Behauptung, die die unabhängige Prüfung nachliest.
"""

import re

ROW_ID = re.compile(r"[A-Z]{2}-\d{2}")


def checks_rights(*row_ids: str):
    """Markiert eine Seite, die die Rechte nach den genannten Zeilen der Rechtematrix prüft."""
    if not row_ids or not all(isinstance(row, str) and ROW_ID.fullmatch(row) for row in row_ids):
        raise ValueError(f"Jede Markierung braucht mindestens eine Kennung der Rechtematrix wie PK-01: {row_ids!r}")

    def mark(view):
        view.rights_rows = row_ids
        return view

    return mark


def without_personal_data(reason: str):
    """Markiert eine Seite ohne Personendaten, mit Begründung."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Jede Seite ohne Personendaten braucht eine Begründung.")

    def mark(view):
        view.no_personal_data = reason
        return view

    return mark
