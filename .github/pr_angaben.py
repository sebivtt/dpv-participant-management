"""Prüfung „PR-Angaben“: Pflichtangaben im Pull Request (#237).

Läuft auf GitHub bei jedem Öffnen, Bearbeiten und neuen Stand eines Pull Requests
(`.github/workflows/pr-angaben.yml`). Sie zeigt, dass die Angaben da sind und zusammenpassen:

- genau ein „Closes #N“, und Issue N trägt das Label `geklärt`;
- die Beschreibung beginnt mit dem Abschnitt „Für Sebastian“: einmal, als erster Abschnitt, 1 bis 5 nicht
  leere Zeilen und höchstens 600 Zeichen (Länge und Platz, nicht ob er verständlich ist);
- ein Link auf einen Kommentar „Szenarien (…)“ aus genau diesem Issue, oder der Verzicht
  „Szenarien: keine, weil …“, den auch der Text des Issues festhält;
- bei Codeänderung ein Test-Commit (nur Tests, mindestens eine Zeile hinzugefügt), vor dem kein
  Code liegt (außer einem genannten Gerüst-Commit), nach dem Code kommt, und der nach der letzten
  Bearbeitung der verlinkten Szenarien-Kommentare entstand. Ohne Codeänderung genügt
  „Test-Commit: entfällt, weil …“.

Sie zeigt nicht, dass so gearbeitet wurde, nicht, dass die Szenarien Sebastians Entscheidungen
enthalten, und nicht, dass der Test aus dem richtigen Grund rot war (`docs/entscheidungen.md`).

Nur Standardbibliothek. Alle Daten holt das Skript bei jedem Lauf frisch von der festen Adresse
unten; aus der Ereignisdatei nimmt es nur die Nummer des Pull Requests. Was nicht vollständig
gelesen werden kann, ist „nicht prüfbar“ und damit rot, nie grün.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime

API = "https://api.github.com/repos/sebivtt/dpv-participant-management"
REPO = API.removeprefix("https://api.github.com/repos/")

SEITENGROESSE = 100
MAX_SEITEN = 50
# Die Liste der Commits eines Pull Requests endet bei 250 Einträgen; mehr wäre nicht zu sehen.
MAX_COMMITS = 250
# Mehr Dateien liefert GitHub je Commit auf der ersten Seite nicht.
MAX_DATEIEN = 300

TESTORDNER = ("tests/", "rauchtests/", "containertests/")
KEIN_CODE = ("docs/", ".github/ISSUE_TEMPLATE/", *TESTORDNER)

# Alle Formen, mit denen GitHub ein Issue schließt: Wort, optional „:“, dann „#N“, „inhaber/repo#N“ oder
# die Adresse des Issues. Erlaubt ist nur „Closes #N“; jede andere Form wäre ein still mitgeschlossenes Issue.
SCHLIESST = re.compile(
    r"\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)(:?)[ \t]+"
    r"(#|[\w.-]+/[\w.-]+#|https?://github\.com/[\w.-]+/[\w.-]+/issues/)(\d+)",
    re.IGNORECASE,
)
SZENARIEN_KOPF = re.compile(r"\s*(?:#+\s*)?(?:\*\*|__)?\s*Szenarien \(")
VERZICHT = re.compile(r"Szenarien:\s*keine\b(.*)", re.IGNORECASE)
VERZICHT_IM_ISSUE = re.compile(r"^[\s>*_-]*(?:\*\*|__)?Szenarien: keine\.(?:\*\*|__)?[ \t]*(.+)$", re.MULTILINE)
KOPF_NAME = "Für Sebastian"
KOPF_MAX_ZEILEN = 5
KOPF_MAX_ZEICHEN = 600
UEBERSCHRIFT = re.compile(r"^## (.*?)[ \t]*$")
CODEZAUN = re.compile(r"^ {0,3}(```|~~~)")
# GitHub blendet ab einem nicht geschlossenen Kommentar den ganzen Rest aus.
OFFENER_KOMMENTAR = re.compile(r"<!--.*\Z", flags=re.DOTALL)
KENNUNG = re.compile(r"[0-9a-f]{7,40}")
ENTFAELLT = re.compile(r"entfällt\b[\s,:;.]*(?:weil\b)?[\s,:;.]*(.*)", re.IGNORECASE)


class NichtPruefbar(Exception):
    """GitHub hat nicht oder nicht vollständig geantwortet."""


# --- Kleine Hilfen ----------------------------------------------------------------------------


def bereinige(text):
    """Fremder Text darf keine Steuerzeile von GitHub („::error::…“) erzeugen: eine Zeile, kein %."""
    text = "".join(" " if zeichen.isspace() or not zeichen.isprintable() else zeichen for zeichen in str(text))
    return text.replace("%", "％")


def _zeitpunkt(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _hat_grund(text):
    return re.search(r"\w", text) is not None


def einheitliche_zeilen(text):
    """Nach einer Bearbeitung im Browser schickt GitHub „\\r\\n“; die Prüfung liest nur „\\n“."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _kurz(commit):
    return commit["sha"][:7]


def ohne_kommentare(text):
    """Die Hinweise der Vorlage stehen in HTML-Kommentaren und zählen nicht als Angabe."""
    return re.sub(r"<!--.*?-->", "", einheitliche_zeilen(text), flags=re.DOTALL)


def wie_geprueft(text):
    """Der Abschnitt „Wie geprüft wurde“ bis zur nächsten Überschrift."""
    treffer = re.search(r"^## Wie geprüft wurde[ \t]*$(.*?)(?=^## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    return treffer.group(1) if treffer else ""


def _zeilenwert(abschnitt, name):
    treffer = re.search(rf"^[ \t]*(?:[-*][ \t]+)?{name}:[ \t]*(.*)$", abschnitt, flags=re.MULTILINE)
    return treffer.group(1).replace("`", "").strip() if treffer else None


def _kommentar_kennungen(abschnitt):
    """Kennungen der Kommentare, auf die der Abschnitt in diesem Repo verlinkt (nur diese Adresse zählt)."""
    muster = rf"https://github\.com/{re.escape(REPO)}/issues/\d+#issuecomment-(\d+)"
    return list(dict.fromkeys(int(kennung) for kennung in re.findall(muster, abschnitt, flags=re.IGNORECASE)))


def szenarien_links(beschreibung):
    """Kennungen der Kommentare, auf die „Wie geprüft wurde“ verlinkt."""
    return _kommentar_kennungen(wie_geprueft(ohne_kommentare(beschreibung)))


def _schliessende(text):
    """Je schließende Angabe: (Wortlaut, erlaubt?, Nummer)."""
    return [
        (t.group(0), t.group(1).lower() == "closes" and not t.group(2) and t.group(3) == "#", int(t.group(4)))
        for t in SCHLIESST.finditer(text)
    ]


def closes_nummer(beschreibung):
    """Die Nummer, wenn genau eine schließende Angabe dasteht und sie „Closes #N“ heißt, sonst None."""
    angaben = _schliessende(ohne_kommentare(beschreibung))
    return angaben[0][2] if len(angaben) == 1 and angaben[0][1] else None


# --- Dateien und Commits ----------------------------------------------------------------------


def ist_test(pfad):
    return pfad.startswith(TESTORDNER)


def ist_code(pfad):
    return not (pfad.startswith(KEIN_CODE) or pfad.endswith(".md"))


def _pfade(commit):
    return [pfad for datei in commit["dateien"] for pfad in (datei["name"], datei.get("vorher")) if pfad]


def ist_abgleich(commit):
    """Merge-Commit (etwa „Update branch“): bringt Code aus `main`, keinen eigenen."""
    return len(commit.get("parents", [])) > 1


def aendert_code(commit):
    return not ist_abgleich(commit) and any(ist_code(pfad) for pfad in _pfade(commit))


def _nur_tests(commit):
    pfade = _pfade(commit)
    return bool(pfade) and all(ist_test(pfad) for pfad in pfade)


def _fuegt_zeilen_hinzu(commit):
    return sum(datei["added"] for datei in commit["dateien"]) > 0


# --- Prüfregeln -------------------------------------------------------------------------------


def _ueberschriften(zeilen):
    """(Zeilennummer, Name) jeder Überschrift „## “, außer in Codeblöcken."""
    funde = []
    zaun = None
    for nummer, zeile in enumerate(zeilen):
        treffer = CODEZAUN.match(zeile)
        if treffer:
            if zaun is None:
                zaun = treffer.group(1)
            elif treffer.group(1) == zaun:
                zaun = None
            continue
        ueberschrift = UEBERSCHRIFT.match(zeile) if zaun is None else None
        if ueberschrift:
            funde.append((nummer, ueberschrift.group(1)))
    return funde


def _pruefe_kopf(text):
    """Der Kopf „Für Sebastian“: einmal, an erster Stelle, 1 bis 5 nicht leere Zeilen, höchstens 600 Zeichen."""
    zeilen = OFFENER_KOMMENTAR.sub("", text).splitlines()
    funde = _ueberschriften(zeilen)
    namen = [name for _, name in funde]
    anzahl = namen.count(KOPF_NAME)
    if anzahl == 0:
        return [
            f"Kopf: Die Beschreibung beginnt nicht mit dem Abschnitt „## {KOPF_NAME}“ "
            "(höchstens fünf Zeilen: was sich ändert, was du ansehen solltest, was offen ist)."
        ]
    erste = funde[0][0]
    if namen[0] != KOPF_NAME or any(zeile.strip() for zeile in zeilen[:erste]):
        return [
            f"Kopf: Der Abschnitt „{KOPF_NAME}“ muss der erste Abschnitt der Beschreibung sein; "
            "davor darf nichts stehen außer HTML-Kommentaren."
        ]
    if anzahl > 1:
        return [f"Kopf: Den Abschnitt „{KOPF_NAME}“ darf es nur einmal geben, gefunden: {anzahl}."]
    ende = funde[1][0] if len(funde) > 1 else len(zeilen)
    inhalt = [zeile.strip() for zeile in zeilen[erste + 1 : ende] if zeile.strip()]
    if not inhalt:
        return [f"Kopf: Der Abschnitt „{KOPF_NAME}“ ist leer; er braucht ein bis fünf Zeilen."]
    mangel = []
    if len(inhalt) > KOPF_MAX_ZEILEN:
        mangel.append(
            f"Kopf: Der Abschnitt „{KOPF_NAME}“ hat {len(inhalt)} Zeilen; erlaubt sind höchstens fünf Zeilen."
        )
    laenge = len("".join(inhalt))
    if laenge > KOPF_MAX_ZEICHEN:
        mangel.append(
            f"Kopf: Der Abschnitt „{KOPF_NAME}“ hat {laenge} Zeichen; erlaubt sind höchstens {KOPF_MAX_ZEICHEN} Zeichen."
        )
    return mangel


def _pruefe_closes(text):
    """Regel 1: genau ein „Closes #N“."""
    mangel = []
    angaben = _schliessende(text)
    anzahl = sum(1 for _, erlaubt, _ in angaben if erlaubt)
    if anzahl != 1:
        mangel.append(f"Closes: Es muss genau ein „Closes #<Nummer>“ stehen, gefunden: {anzahl}.")
    for wortlaut, erlaubt, _ in angaben:
        if not erlaubt or anzahl > 1:
            mangel.append(
                f"Closes: „{wortlaut}“ ist nicht erlaubt; es schließt auf GitHub ein Issue, die Regel nennt genau ein "
                "„Closes #<Nummer>“."
            )
    return mangel


def _pruefe_issue(nummer, issue):
    """Regel 1 und 2: Das Issue gibt es und trägt `geklärt`."""
    if issue is None:
        return [f"Issue: #{nummer} gibt es in diesem Repo nicht."]
    if "geklärt" not in issue["labels"]:
        return [f"Label: Issue #{nummer} trägt das Label „geklärt“ nicht; umgesetzt wird nur ein geklärtes Issue."]
    return []


def _sortiere_links(abschnitt, nummer, kommentare):
    gueltig, probleme = [], []
    for kennung in _kommentar_kennungen(abschnitt):
        kommentar = kommentare.get(kennung)
        if kommentar is None:
            probleme.append(f"Kommentar {kennung} nicht gefunden.")
        elif kommentar["issue"] is None:
            probleme.append(f"Kommentar {kennung} gehört nicht zu diesem Repo.")
        elif kommentar["issue"] != nummer:
            probleme.append(f"Kommentar {kennung} gehört zu Issue #{kommentar['issue']}, nicht zu #{nummer}.")
        elif not SZENARIEN_KOPF.match(kommentar["body"]):
            probleme.append(f"Kommentar {kennung} beginnt nicht mit „Szenarien (“.")
        else:
            gueltig.append((kennung, kommentar))
    return gueltig, probleme


def _pruefe_verzicht(abschnitt, nummer, issue):
    """Regel 3, Verzicht: Grund in der Beschreibung und die Zeile „Szenarien: keine.“ im Issue."""
    verzicht = next((m for m in map(VERZICHT.search, abschnitt.splitlines()) if m), None)
    if verzicht is None:
        return None
    grund = re.sub(r"^[\s,:;.]*(?:weil\b)?[\s,:;.]*", "", verzicht.group(1), flags=re.IGNORECASE)
    if not _hat_grund(grund):
        return ["Szenarien: Der Verzicht „Szenarien: keine“ steht da, aber ohne Grund („Szenarien: keine, weil …“)."]
    if issue is not None and not _hat_grund("".join(VERZICHT_IM_ISSUE.findall(issue["body"]))):
        return [
            f"Szenarien: Der Verzicht steht in der Beschreibung, aber im Text von Issue #{nummer} "
            "fehlt die Zeile „Szenarien: keine.“ mit einem Grund."
        ]
    return []


def _pruefe_szenarien(abschnitt, nummer, issue, kommentare):
    """Regel 3. Gibt die Mängel und die gültigen Szenarien-Kommentare zurück."""
    if nummer is None:
        return [], []
    gueltig, probleme = _sortiere_links(abschnitt, nummer, kommentare)
    if gueltig:
        return [], gueltig
    verzicht = _pruefe_verzicht(abschnitt, nummer, issue)
    if verzicht is not None:
        return verzicht, []
    hinweis = " ".join(probleme)
    return [
        f"Szenarien: Es steht kein Link auf einen Kommentar „Szenarien (…)“ aus Issue #{nummer} im Abschnitt "
        f"„Wie geprüft wurde“ und kein Verzicht „Szenarien: keine, weil …“. {hinweis}".strip()
    ], []


def _finde_commits(name, wert, commits):
    """Ordnet die genannten Kennungen Commits des Pull Requests zu. Gibt (Treffer, Mängel) zurück."""
    treffer, mangel = [], []
    for wort in (w for w in re.split(r"[\s,;]+", wert) if w):
        if not KENNUNG.fullmatch(wort.lower()):
            mangel.append(f"{name}: „{wort}“ ist keine gültige Kennung eines Commits.")
            continue
        passend = [c for c in commits if c["sha"].startswith(wort.lower())]
        if not passend:
            mangel.append(f"{name}: {wort} gehört nicht zu den Commits dieses Pull Requests.")
        elif len(passend) > 1:
            mangel.append(f"{name}: {wort} ist nicht eindeutig; nenne mehr Zeichen der Kennung.")
        else:
            treffer.append(passend[0])
    return treffer, mangel


def _pruefe_test_commit_selbst(commit):
    if not _nur_tests(commit):
        return [
            f"Test-Commit: {_kurz(commit)} ändert nicht nur Tests, sondern auch anderes; "
            "ein Test-Commit enthält nur Dateien aus den Testordnern."
        ]
    if not _fuegt_zeilen_hinzu(commit):
        return [f"Test-Commit: {_kurz(commit)} fügt in den Tests nichts hinzu (reines Löschen genügt nicht)."]
    return []


def _pruefe_reihenfolge(commits, tests, geruest):
    """Regel 4 (b) und (c): kein Code vor dem ersten, ein Commit mit Code nach dem letzten Test-Commit."""
    stellen = [commits.index(c) for c in tests]
    erster, letzter = min(stellen), max(stellen)
    mangel = []
    zu_frueh = [_kurz(c) for c in commits[:erster] if aendert_code(c) and c not in geruest]
    if zu_frueh:
        mangel.append(
            f"Test-Commit: Commit {', '.join(zu_frueh)} ändert Code vor dem ersten Test-Commit ({_kurz(commits[erster])}); "
            "ein leeres Gerüst davor muss als „Gerüst-Commit:“ genannt sein."
        )
    if not any(aendert_code(c) for c in commits[letzter + 1 :]):
        mangel.append(
            f"Test-Commit: Der Pull Request ändert Code, aber nach dem letzten Test-Commit ({_kurz(commits[letzter])}) "
            "ändert kein Commit Code."
        )
    return mangel


def _pruefe_kommentar_zeiten(tests, gueltige):
    """Regel 4 (d): Zu jedem Szenarien-Kommentar gibt es einen Test-Commit nach dessen letzter Bearbeitung."""
    mangel = []
    for kennung, kommentar in gueltige:
        bearbeitet = _zeitpunkt(kommentar["updated_at"])
        if not any(_zeitpunkt(c["committed"]) >= bearbeitet for c in tests):
            mangel.append(
                f"Test-Commit: Der Szenarien-Kommentar {kennung} wurde nach dem Test-Commit bearbeitet; "
                "nenne einen Test-Commit, der danach entstand (Szenarien und Tests passen sonst nicht zusammen)."
            )
    return mangel


def _pruefe_entfaellt(treffer, code_geaendert):
    if code_geaendert:
        return [
            "Test-Commit: „entfällt“ steht da, obwohl der Pull Request Code ändert; "
            "nenne die Kennung des Commits, der nur Tests hinzufügt und vor dem Code liegt."
        ]
    if not _hat_grund(treffer.group(1)):
        return ["Test-Commit: „entfällt“ steht da, aber ohne Grund („Test-Commit: entfällt, weil …“)."]
    return []


def _pruefe_test_commits(abschnitt, commits, gueltige):
    """Regel 4: Test-Commit vor dem Code."""
    code_geaendert = any(aendert_code(c) for c in commits)
    wert = _zeilenwert(abschnitt, "Test-Commit")
    if wert is None:
        return [
            "Test-Commit: Die Zeile „- Test-Commit: <Kennung>“ fehlt im Abschnitt „Wie geprüft wurde“ "
            "(ohne Codeänderung: „- Test-Commit: entfällt, weil …“)."
        ]
    entfaellt = ENTFAELLT.match(wert)
    if entfaellt:
        return _pruefe_entfaellt(entfaellt, code_geaendert)
    if not wert:
        return ["Test-Commit: Die Zeile „Test-Commit:“ steht da, aber ohne Kennung."]
    tests, mangel = _finde_commits("Test-Commit", wert, commits)
    geruest, mehr = _finde_commits("Gerüst-Commit", _zeilenwert(abschnitt, "Gerüst-Commit") or "", commits)
    mangel += mehr
    for commit in tests:
        mangel += _pruefe_test_commit_selbst(commit)
    if code_geaendert and tests:
        mangel += _pruefe_reihenfolge(commits, tests, geruest)
        mangel += _pruefe_kommentar_zeiten(tests, gueltige)
    return mangel


def pruefe(beschreibung, issue, kommentare, commits):
    """Alle Mängel in Alltagssprache; leer heißt: alle Pflichtangaben sind da und passen zusammen.

    beschreibung: Text der Beschreibung des Pull Requests.
    issue:        None oder {"number", "body", "labels": [Namen]} des Issues aus „Closes #N“.
    kommentare:   {Kennung: None oder {"issue", "body", "updated_at"}} der verlinkten Kommentare.
    commits:      in Abstammungsfolge (ältester zuerst), je {"sha", "committed",
                  "dateien": [{"name", "vorher", "added", "deleted"}]}.
    """
    text = ohne_kommentare(beschreibung)
    if issue is not None:
        issue = {**issue, "body": einheitliche_zeilen(issue["body"])}
    abschnitt = wie_geprueft(text)
    mangel = _pruefe_kopf(text)
    mangel += _pruefe_closes(text)
    nummer = closes_nummer(beschreibung)
    if nummer is not None:
        mangel += _pruefe_issue(nummer, issue)
    szenarien, gueltige = _pruefe_szenarien(abschnitt, nummer, issue, kommentare)
    mangel += szenarien
    mangel += _pruefe_test_commits(abschnitt, commits, gueltige)
    return [bereinige(meldung) for meldung in mangel]


# --- Abfrage der GitHub-Schnittstelle ---------------------------------------------------------


def abstammung_ordnen(commits):
    """Ältester Commit zuerst, nach den Vorgängern („parents“), nicht nach der Zeit."""
    vorhanden = {c["sha"] for c in commits}
    fertig, offen, ergebnis = set(), list(commits), []
    while offen:
        bereit = next((c for c in offen if all(p in fertig or p not in vorhanden for p in c["parents"])), None)
        if bereit is None:
            raise NichtPruefbar("Die Commits lassen sich nicht in eine Reihenfolge bringen.")
        ergebnis.append(bereit)
        fertig.add(bereit["sha"])
        offen.remove(bereit)
    return ergebnis


def liste_lesen(abrufen, pfad):
    """Liest alle Seiten einer Liste."""
    ergebnis = []
    trenner = "&" if "?" in pfad else "?"
    for seite in range(1, MAX_SEITEN + 1):
        antwort = abrufen(f"{pfad}{trenner}per_page={SEITENGROESSE}&page={seite}")
        if not isinstance(antwort, list):
            raise NichtPruefbar(f"GitHub hat keine Liste für {pfad} geliefert.")
        ergebnis += antwort
        if len(antwort) < SEITENGROESSE:
            return ergebnis
    raise NichtPruefbar(f"Die Liste {pfad} ist zu lang.")


def _lese_commits(nummer, abrufen):
    roh = liste_lesen(abrufen, f"/pulls/{nummer}/commits")
    if len(roh) >= MAX_COMMITS:
        raise NichtPruefbar("Der Pull Request hat 250 oder mehr Commits; GitHub liefert sie nicht vollständig.")
    commits = [
        {"sha": c["sha"], "parents": [p["sha"] for p in c["parents"]], "committed": c["commit"]["committer"]["date"]}
        for c in roh
    ]
    for commit in abstammung_ordnen(commits):
        if not re.fullmatch(r"[0-9a-f]{40}", commit["sha"]):
            raise NichtPruefbar("Unerwartete Kennung eines Commits.")
        antwort = abrufen(f"/commits/{commit['sha']}")
        if antwort is None or len(antwort["files"]) >= MAX_DATEIEN:
            raise NichtPruefbar(f"Die Dateien von Commit {commit['sha'][:7]} sind nicht vollständig lesbar.")
        commit["dateien"] = [
            {"name": d["filename"], "vorher": d.get("previous_filename"), "added": d["additions"], "deleted": d["deletions"]}
            for d in antwort["files"]
        ]
        yield commit


def _lese_issue(nummer, abrufen):
    roh = abrufen(f"/issues/{nummer}")
    if roh is None or "pull_request" in roh:
        return None, None
    if "url" in roh and not roh["url"].startswith(f"{API}/issues/"):
        raise NichtPruefbar(f"Issue #{nummer} liegt inzwischen in einem anderen Repo.")
    issue = {"number": nummer, "body": roh["body"] or "", "labels": [label["name"] for label in roh["labels"]]}
    return issue, roh.get("updated_at")


def _lese_kommentare(beschreibung, abrufen):
    kommentare = {}
    for kennung in szenarien_links(beschreibung):
        roh = abrufen(f"/issues/comments/{kennung}")
        if roh is None:
            kommentare[kennung] = None
        else:
            adresse = roh["issue_url"].rstrip("/")
            nummer = int(adresse.rsplit("/", 1)[1]) if adresse.startswith(f"{API}/issues/") else None
            kommentare[kennung] = {"issue": nummer, "body": roh["body"] or "", "updated_at": roh["updated_at"]}
    return kommentare


def _pruefe_pull_request(nummer, abrufen):
    roh = abrufen(f"/pulls/{nummer}")
    if roh is None:
        raise NichtPruefbar(f"Pull Request #{nummer} nicht gefunden.")
    beschreibung = roh["body"] or ""
    stand = [f"Gelesen: Pull Request #{nummer}, zuletzt geändert {roh['updated_at']}."]
    issue, issue_geaendert = None, None
    issue_nummer = closes_nummer(beschreibung)
    if issue_nummer is not None:
        issue, issue_geaendert = _lese_issue(issue_nummer, abrufen)
    if issue is not None:
        label = "ja" if "geklärt" in issue["labels"] else "nein"
        stand.append(f"Gelesen: Issue #{issue_nummer}, zuletzt geändert {issue_geaendert}, Label „geklärt“: {label}.")
    kommentare = _lese_kommentare(beschreibung, abrufen)
    commits = list(_lese_commits(nummer, abrufen))
    stand.append(f"Gelesen: {len(commits)} Commits und {len(kommentare)} verlinkte Kommentare.")
    return pruefe(beschreibung, issue, kommentare, commits), stand


def pruefe_pull_request(nummer, abrufen):
    """Liest alles frisch von GitHub und prüft. Gibt (Mängel, gelesener Stand) zurück; Ausfall ist rot."""
    try:
        return _pruefe_pull_request(nummer, abrufen)
    except NichtPruefbar as fehler:
        return [bereinige(f"nicht prüfbar: {fehler}")], []
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as fehler:
        return [bereinige(f"nicht prüfbar: unerwartete Antwort von GitHub ({type(fehler).__name__}: {fehler})")], []


def github_abrufen(token):
    """Abruf mit fester Adresse; der Pfad kommt nie aus einem Link (immer mit „/“ beginnend)."""

    def abrufen(pfad):
        if not pfad.startswith("/"):
            raise NichtPruefbar("Ungültiger Pfad.")
        kopf = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        anfrage = urllib.request.Request(API + pfad, headers=kopf)  # noqa: S310 (feste https-Adresse)
        if token:
            # Nicht bei einer Weiterleitung mitschicken: der Schlüssel geht nur an die feste Adresse.
            anfrage.add_unredirected_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(anfrage, timeout=30) as antwort:  # noqa: S310 (feste https-Adresse)
                return json.load(antwort)
        except urllib.error.HTTPError as fehler:
            if fehler.code == 404:
                return None
            raise NichtPruefbar(f"GitHub antwortet mit Fehler {fehler.code}.") from fehler
        except (urllib.error.URLError, TimeoutError, ValueError) as fehler:
            raise NichtPruefbar("GitHub ist nicht erreichbar oder antwortet unlesbar.") from fehler

    return abrufen


def _nummer_aus_ereignis(pfad):
    with open(pfad, encoding="utf-8") as datei:
        nummer = json.load(datei)["pull_request"]["number"]
    if not isinstance(nummer, int) or nummer < 1:
        raise ValueError("Ungültige Nummer.")
    return nummer


def _ausgeben(zeile):
    sys.stdout.write(bereinige(zeile) + "\n")


def main(umgebung=None):
    umgebung = os.environ if umgebung is None else umgebung
    try:
        nummer = _nummer_aus_ereignis(umgebung["GITHUB_EVENT_PATH"])
    except (KeyError, OSError, ValueError, TypeError):
        _ausgeben("::error title=PR-Angaben::nicht prüfbar: Die Ereignisdatei nennt keinen Pull Request.")
        return 1
    mangel, stand = pruefe_pull_request(nummer, github_abrufen(umgebung.get("GITHUB_TOKEN", "")))
    for meldung in mangel:
        _ausgeben(f"::error title=PR-Angaben::{meldung}")
    for zeile in stand:
        _ausgeben(zeile)
    _ausgeben("PR-Angaben: Es fehlt etwas (siehe oben)." if mangel else "PR-Angaben: Alle Pflichtangaben sind da.")
    return 1 if mangel else 0


if __name__ == "__main__":
    sys.exit(main())
