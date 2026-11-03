"""Prüfung „PR-Angaben“ (#237): Pflichtangaben im Pull Request.

Gerüst: Die Funktionen sind noch leer, damit die Tests an der Regel scheitern und nicht daran,
dass etwas fehlt (CONTRIBUTING.md, Abschnitt 3).
"""

REPO = "sebivtt/dpv-participant-management"


class NichtPruefbar(Exception):
    """GitHub hat nicht oder nicht vollständig geantwortet."""


def pruefe(beschreibung, issue, kommentare, commits, repo=REPO):
    return []


def bereinige(text):
    return text


def abstammung_ordnen(commits):
    return list(commits)


def liste_lesen(abrufen, pfad):
    return []


def pruefe_pull_request(nummer, abrufen):
    return [], []
