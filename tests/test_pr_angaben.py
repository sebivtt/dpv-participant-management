"""Tests für die Prüfung „PR-Angaben“ (.github/pr_angaben.py, .github/workflows/pr-angaben.yml), #237.

Die Prüfung zeigt, dass die Pflichtangaben im Pull Request da sind und zusammenpassen: genau ein
„Closes #…“, ein Issue mit dem Label `geklärt`, ein Link auf den Kommentar „Szenarien (…)“ aus genau
diesem Issue (oder der begründete Verzicht) und ein Test-Commit, der vor dem Code liegt. Sie zeigt nicht,
dass so gearbeitet wurde, und nicht, dass die Tests aus dem richtigen Grund rot waren (`docs/entscheidungen.md`).

Alles läuft mit erfundenen Beschreibungen, Issues, Kommentaren und Commits, ohne Netz. Ob GitHub den
Ablauf so ausführt, zeigt erst die Probe am eigenen Pull Request.
"""

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
SKRIPT = BASE_DIR / ".github" / "pr_angaben.py"
ABLAUF = BASE_DIR / ".github" / "workflows" / "pr-angaben.yml"
CI = BASE_DIR / ".github" / "workflows" / "ci.yml"
VORLAGE = BASE_DIR / ".github" / "pull_request_template.md"
REPO = "sebivtt/dpv-participant-management"

_spec = importlib.util.spec_from_file_location("pr_angaben", SKRIPT)
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)


# --- Bausteine für erfundene Pull Requests ----------------------------------------------------


def _sha(n):
    """Erfundene Commit-Kennung: die ersten sieben Zeichen nennt die Beschreibung."""
    return f"{n:07x}" + "0" * 33


def _kurz(n):
    return _sha(n)[:7]


def _zeit(minute):
    return f"2026-11-03T10:{minute:02d}:00Z"


def _datei(name, added=3, deleted=0, vorher=None):
    return {"name": name, "vorher": vorher, "added": added, "deleted": deleted}


def _commit(n, minute, *dateien):
    return {"sha": _sha(n), "committed": _zeit(minute), "dateien": list(dateien)}


def _tests(n, minute):
    return _commit(n, minute, _datei("tests/test_neu.py", added=12))


def _code(n, minute):
    return _commit(n, minute, _datei("config/neu.py", added=8), _datei("docs/neu.md", added=2))


def _link(issue=12, kommentar=500, text="Szenarien (03.11.2026)"):
    return f"[{text}](https://github.com/{REPO}/issues/{issue}#issuecomment-{kommentar})"


TEST_COMMIT_STANDARD = "- Test-Commit: " + _kurz(1)


def _beschreibung(
    closes="- Closes #12",
    szenarien=None,
    test_commit=TEST_COMMIT_STANDARD,
    geruest=None,
    davor="",
):
    zeilen = ["## Was sich für Nutzende ändert", "", "Nichts.", "", "## Anforderungen und Entscheidungen", "", closes]
    zeilen += ["", davor, "", "## Wie geprüft wurde", ""]
    zeilen.append(szenarien if szenarien is not None else "- Szenarien: " + _link())
    if test_commit:
        zeilen.append(test_commit)
    if geruest:
        zeilen.append(geruest)
    zeilen += ["- Test für den erlaubten Fall: ok", "", "## Nicht geprüft und offen", "", "Nichts."]
    return "\n".join(zeilen)


def _issue(body="Anforderung.", labels=("geklärt", "enhancement"), nummer=12):
    return {"number": nummer, "body": body, "labels": list(labels)}


def _kommentar(issue=12, body="**Szenarien (03.11.2026)**\n\n1. Fall.", minute=5):
    return {"issue": issue, "body": body, "updated_at": _zeit(minute)}


def _ok(**aenderungen):
    """Ein vollständiger Pull Request: Szenarien, Test-Commit, danach Code."""
    angaben = {
        "beschreibung": _beschreibung(),
        "issue": _issue(),
        "kommentare": {500: _kommentar()},
        "commits": [_tests(1, 10), _code(2, 20)],
    }
    angaben.update(aenderungen)
    return angaben


def _pruefe(**aenderungen):
    return pa.pruefe(**_ok(**aenderungen))


def _gruen(**aenderungen):
    assert _pruefe(**aenderungen) == []


def _rot(*teile, **aenderungen):
    """Es gibt einen Mangel, der alle genannten Textteile enthält."""
    mangel = _pruefe(**aenderungen)
    assert any(all(teil in m for teil in teile) for m in mangel), (teile, mangel)
    return mangel


VERZICHT_ISSUE = "Anforderung.\n\nSzenarien: keine. Das Issue hat kein fachliches Verhalten des Tools."
DOKU_COMMITS = [_commit(1, 10, _datei("CLAUDE.md", added=4), _datei("docs/entscheidungen.md", added=9))]


# --- Grün -------------------------------------------------------------------------------------


def test_vollstaendiger_pull_request_ist_gruen():
    _gruen()


def test_die_ausgefuellte_neue_vorlage_ist_gruen():
    text = VORLAGE.read_text(encoding="utf-8")
    text = text.replace("## Anforderungen und Entscheidungen\n", "## Anforderungen und Entscheidungen\n\n- Closes #12\n")
    text = re.sub(r"^- Szenarien.*$", "- Szenarien: " + _link(), text, flags=re.M)
    text = text.replace("- Test-Commit:", "- Test-Commit: " + _kurz(1))

    _gruen(beschreibung=text)


def test_hinweise_in_html_kommentaren_der_vorlage_zaehlen_nicht():
    davor = "<!-- Beispiel: Closes #99\n- Test-Commit: entfällt, weil nichts -->"

    _gruen(beschreibung=_beschreibung(davor=davor))


def test_kommentar_als_ueberschrift_gilt_als_szenarien_kommentar():
    _gruen(kommentare={500: _kommentar(body="### Szenarien (03.11.2026)\n\n1. Fall.")})


def test_zwei_links_in_einer_zeile_wie_bei_213_sind_gruen():
    zeile = f"- Szenarien: {_link()} und {_link(kommentar=501, text='Szenarien (04.11.2026)')}"

    _gruen(beschreibung=_beschreibung(szenarien=zeile), kommentare={500: _kommentar(), 501: _kommentar(minute=6)})


def test_nachtrag_in_eigener_zeile_mit_zweitem_test_commit_wie_bei_223_ist_gruen():
    szenarien = f"- Szenarien: {_link()}\n  Nachtrag: {_link(kommentar=501, text='Szenarien (05.11.2026)')}"
    commits = [_tests(1, 10), _code(2, 20), _tests(3, 35), _code(4, 40)]

    _gruen(
        beschreibung=_beschreibung(szenarien=szenarien, test_commit=f"- Test-Commit: {_kurz(1)}, {_kurz(3)}"),
        kommentare={500: _kommentar(), 501: _kommentar(minute=30)},
        commits=commits,
    )


def test_geruest_dann_test_dann_code_ist_gruen():
    geruest = _commit(1, 5, _datei("config/neu.py", added=4))

    _gruen(
        beschreibung=_beschreibung(test_commit=f"- Test-Commit: {_kurz(2)}", geruest=f"- Gerüst-Commit: {_kurz(1)}"),
        commits=[geruest, _tests(2, 10), _code(3, 20)],
    )


def test_nachbesserung_test_code_test_code_ist_gruen():
    _gruen(commits=[_tests(1, 10), _code(2, 20), _tests(3, 30), _code(4, 40)])


def test_hilfsdatei_in_einem_testordner_zaehlt_als_test():
    test_commit = _commit(1, 10, _datei("tests/conftest.py", added=2), _datei("rauchtests/hilfe.py", added=1))

    _gruen(commits=[test_commit, _code(2, 20)])


def test_doku_pull_request_mit_verzicht_und_entfaellt_ist_gruen():
    _gruen(
        beschreibung=_beschreibung(
            szenarien="- Szenarien: keine, weil das Issue kein fachliches Verhalten hat.",
            test_commit="- Test-Commit: entfällt, weil nur Regeltexte geändert sind.",
        ),
        issue=_issue(body=VERZICHT_ISSUE),
        kommentare={},
        commits=DOKU_COMMITS,
    )


def test_verzicht_im_issue_darf_fett_geschrieben_sein():
    _gruen(
        beschreibung=_beschreibung(
            szenarien="- Szenarien: keine. Grund steht im Issue.",
            test_commit="- Test-Commit: entfällt, weil nur Doku.",
        ),
        issue=_issue(body="Text\n\n**Szenarien: keine.** Reine Doku ohne Verhalten."),
        kommentare={},
        commits=DOKU_COMMITS,
    )


def test_pull_request_nur_mit_tests_und_entfaellt_ist_gruen():
    _gruen(
        beschreibung=_beschreibung(test_commit="- Test-Commit: entfällt, weil nur Tests dazukommen."),
        commits=[_tests(1, 10)],
    )


def test_ci_pull_request_mit_verzicht_auf_szenarien_und_mit_test_commit_ist_gruen():
    ablauf = _commit(2, 20, _datei(".github/workflows/neu.yml", added=30))

    _gruen(
        beschreibung=_beschreibung(szenarien="- Szenarien: keine, weil der Ablauf kein Verhalten des Tools hat."),
        issue=_issue(body=VERZICHT_ISSUE),
        kommentare={},
        commits=[_tests(1, 10), ablauf],
    )


def test_commit_zeiten_mit_zeitzone_werden_als_zeitpunkte_verglichen():
    spaeter = _tests(1, 10) | {"committed": "2026-11-03T11:10:00+01:00"}  # 10:10 Uhr UTC, nach 10:05 Uhr

    _gruen(commits=[spaeter, _code(2, 20)])


# --- Rot: Closes und Issue --------------------------------------------------------------------


def test_ohne_closes_ist_rot():
    _rot("Closes", "genau ein", beschreibung=_beschreibung(closes="- Siehe Issue 12"))


def test_zwei_closes_sind_rot():
    _rot("Closes", "genau ein", beschreibung=_beschreibung(closes="- Closes #12\n- Closes #13"))


def test_fixes_statt_closes_ist_rot_mit_hinweis():
    _rot("Closes", "nicht erlaubt", beschreibung=_beschreibung(closes="- Fixes #12"))


def test_ein_issue_das_es_nicht_gibt_ist_rot():
    _rot("Issue", "gibt es in diesem Repo nicht", issue=None)


def test_issue_ohne_label_geklaert_ist_rot():
    _rot("Label", "geklärt", issue=_issue(labels=("enhancement",)))


# --- Rot: Szenarien ---------------------------------------------------------------------------


def test_ohne_szenarien_link_und_ohne_verzicht_ist_rot():
    _rot("Szenarien", "kein Link", beschreibung=_beschreibung(szenarien="- Szenarien:"))


def test_link_auf_kommentar_eines_anderen_issues_ist_rot():
    _rot("Szenarien", "gehört zu Issue #5", kommentare={500: _kommentar(issue=5)})


def test_link_auf_kommentar_ohne_szenarien_am_anfang_ist_rot():
    _rot("Szenarien", "beginnt nicht mit", kommentare={500: _kommentar(body="Kurzer Hinweis zum Issue.")})


def test_link_auf_unbekannten_kommentar_ist_rot():
    _rot("Szenarien", "nicht gefunden", kommentare={500: None})


def test_verzicht_ohne_vermerk_im_issue_ist_rot():
    _rot(
        "Szenarien",
        "fehlt die Zeile „Szenarien: keine.“",
        beschreibung=_beschreibung(
            szenarien="- Szenarien: keine, weil kein Verhalten.", test_commit="- Test-Commit: entfällt, weil Doku."
        ),
        kommentare={},
        commits=DOKU_COMMITS,
    )


def test_verzicht_mit_leerem_grund_in_der_beschreibung_ist_rot():
    for zeile in ["- Szenarien: keine.", "- Szenarien: keine, weil"]:
        _rot(
            "Szenarien",
            "ohne Grund",
            beschreibung=_beschreibung(szenarien=zeile, test_commit="- Test-Commit: entfällt, weil Doku."),
            issue=_issue(body=VERZICHT_ISSUE),
            kommentare={},
            commits=DOKU_COMMITS,
        )


def test_verzicht_mit_leerem_grund_im_issue_ist_rot():
    _rot(
        "Szenarien",
        "fehlt die Zeile „Szenarien: keine.“",
        beschreibung=_beschreibung(
            szenarien="- Szenarien: keine, weil kein Verhalten.", test_commit="- Test-Commit: entfällt, weil Doku."
        ),
        issue=_issue(body="Text\n\nSzenarien: keine."),
        kommentare={},
        commits=DOKU_COMMITS,
    )


def test_szenarien_kommentar_nach_dem_test_commit_bearbeitet_ist_rot():
    _rot("Test-Commit", "bearbeitet", kommentare={500: _kommentar(minute=15)})


def test_commit_zeit_vor_der_bearbeitung_ist_in_anderer_zeitzone_rot():
    zu_frueh = _tests(1, 10) | {"committed": "2026-11-03T10:10:00+01:00"}  # 09:10 Uhr UTC, vor 10:05 Uhr

    _rot("Test-Commit", "bearbeitet", commits=[zu_frueh, _code(2, 20)])


def test_zweiter_szenarien_kommentar_braucht_einen_eigenen_spaeteren_test_commit():
    szenarien = f"- Szenarien: {_link()}\n  Nachtrag: {_link(kommentar=501, text='Szenarien (05.11.2026)')}"

    _rot("Test-Commit", "bearbeitet", beschreibung=_beschreibung(szenarien=szenarien),
         kommentare={500: _kommentar(), 501: _kommentar(minute=30)})


# --- Rot: Test-Commit -------------------------------------------------------------------------


def test_ohne_zeile_test_commit_bei_codeaenderung_ist_rot():
    _rot("Test-Commit", "fehlt", beschreibung=_beschreibung(test_commit=None))


def test_zeile_test_commit_ohne_kennung_ist_rot():
    _rot("Test-Commit", "ohne Kennung", beschreibung=_beschreibung(test_commit="- Test-Commit:"))


def test_test_commit_der_nicht_zum_pull_request_gehoert_ist_rot():
    _rot("Test-Commit", "gehört nicht zu den Commits", beschreibung=_beschreibung(test_commit="- Test-Commit: 9999999"))


def test_kennung_die_keine_kennung_ist_rot_und_die_meldung_bleibt_eine_zeile():
    mangel = _rot("Test-Commit", "keine gültige Kennung", beschreibung=_beschreibung(test_commit="- Test-Commit: gleich%0A::error::x"))

    for meldung in mangel:
        assert "\n" not in meldung
        assert "%" not in meldung


def test_test_commit_der_auch_code_aendert_ist_rot():
    zusammen = _commit(1, 10, _datei("tests/test_neu.py", added=12), _datei("config/neu.py", added=8))

    _rot("Test-Commit", "ändert nicht nur Tests", commits=[zusammen, _code(2, 20)])


def test_code_dann_test_dann_codekosmetik_ist_rot():
    _rot("Test-Commit", "vor dem ersten Test-Commit", commits=[_code(1, 5), _tests(2, 10), _code(3, 20)],
         beschreibung=_beschreibung(test_commit=f"- Test-Commit: {_kurz(2)}"))


def test_geruest_das_nicht_genannt_ist_zaehlt_als_code_vor_dem_test_commit():
    geruest = _commit(1, 5, _datei("config/neu.py", added=4))

    _rot("Test-Commit", "vor dem ersten Test-Commit", commits=[geruest, _tests(2, 10), _code(3, 20)],
         beschreibung=_beschreibung(test_commit=f"- Test-Commit: {_kurz(2)}"))


def test_genanntes_geruest_das_nicht_zum_pull_request_gehoert_ist_rot():
    _rot("Gerüst-Commit", "gehört nicht zu den Commits", beschreibung=_beschreibung(geruest="- Gerüst-Commit: 9999999"))


def test_test_commit_der_nur_zeilen_loescht_ist_rot():
    loescht = _commit(1, 10, _datei("tests/test_alt.py", added=0, deleted=14))

    _rot("Test-Commit", "fügt in den Tests nichts hinzu", commits=[loescht, _code(2, 20)])


def test_ohne_code_nach_dem_test_commit_ist_rot():
    _rot("Test-Commit", "nach dem letzten Test-Commit", commits=[_code(1, 5), _tests(2, 10)],
         beschreibung=_beschreibung(test_commit=f"- Test-Commit: {_kurz(2)}", geruest=f"- Gerüst-Commit: {_kurz(1)}"))


def test_entfaellt_bei_codeaenderung_ist_rot():
    _rot("Test-Commit", "obwohl", beschreibung=_beschreibung(test_commit="- Test-Commit: entfällt, weil klein."))


def test_entfaellt_ohne_grund_ist_rot():
    _rot(
        "Test-Commit",
        "ohne Grund",
        beschreibung=_beschreibung(test_commit="- Test-Commit: entfällt, weil"),
        commits=DOKU_COMMITS,
    )


def test_genannte_kennung_ohne_codeaenderung_wird_trotzdem_geprueft():
    _rot("Test-Commit", "gehört nicht zu den Commits",
         beschreibung=_beschreibung(test_commit="- Test-Commit: 9999999"), commits=DOKU_COMMITS)


# --- Abfrage der Schnittstelle ----------------------------------------------------------------


def _antworten(commits, beschreibung=None, issue=None, kommentare=None):
    """Erfundene Antworten der GitHub-Schnittstelle, nach Adresse (Seite 1 ohne Zusatz)."""
    beschreibung = beschreibung or _beschreibung()
    antworten = {
        "/pulls/12": {"number": 12, "body": beschreibung, "updated_at": _zeit(30)},
        "/issues/12": {
            "number": 12,
            "body": "Anforderung.",
            "labels": [{"name": "geklärt"}],
            "updated_at": _zeit(1),
        },
        "/issues/comments/500": {
            "issue_url": f"https://api.github.com/repos/{REPO}/issues/12",
            "body": "**Szenarien (03.11.2026)**",
            "updated_at": _zeit(5),
        },
    }
    if issue is not None:
        antworten["/issues/12"] = issue
    if kommentare is not None:
        antworten.update(kommentare)
    antworten["/pulls/12/commits"] = [
        {
            "sha": c["sha"],
            "parents": [{"sha": vorgaenger}] if vorgaenger else [],
            "commit": {"committer": {"date": c["committed"]}},
        }
        for c, vorgaenger in commits
    ]
    for c, _ in commits:
        antworten[f"/commits/{c['sha']}"] = {
            "files": [
                {"filename": d["name"], "additions": d["added"], "deletions": d["deleted"]} for d in c["dateien"]
            ]
        }
    return antworten


class _Schnittstelle:
    """Ersatz für den Abruf: liefert die Antworten, merkt sich die Adressen, scheitert auf Wunsch."""

    def __init__(self, antworten, fehler=None):
        self.antworten = antworten
        self.fehler = fehler
        self.adressen = []

    def __call__(self, pfad):
        self.adressen.append(pfad)
        if self.fehler:
            raise self.fehler
        basis, _, abfrage = pfad.partition("?")
        antwort = self.antworten.get(basis)
        if isinstance(antwort, list):
            seite = int(re.search(r"page=(\d+)", abfrage).group(1))
            return antwort[(seite - 1) * 100 : seite * 100]
        return antwort


def _kette(*commits):
    """Commits als Kette: jeder hat den vorigen als Vorgänger."""
    return [(c, commits[i - 1]["sha"] if i else None) for i, c in enumerate(commits)]


def test_ganze_abfrage_ordnet_die_commits_nach_der_abstammung_und_ist_gruen():
    kette = _kette(_tests(1, 10), _code(2, 20))
    # Die Schnittstelle nennt die Commits hier in falscher Reihenfolge; maßgeblich ist die Abstammung.
    mangel, stand = pa.pruefe_pull_request(12, _Schnittstelle(_antworten(list(reversed(kette)))))

    assert mangel == []
    assert any("geklärt" in zeile for zeile in stand)


def test_ganze_abfrage_findet_code_vor_dem_test_commit_auch_bei_falscher_reihenfolge_der_antwort():
    kette = _kette(_code(1, 5), _tests(2, 10), _code(3, 20))
    beschreibung = _beschreibung(test_commit=f"- Test-Commit: {_kurz(2)}")

    mangel, _ = pa.pruefe_pull_request(12, _Schnittstelle(_antworten(list(reversed(kette)), beschreibung=beschreibung)))

    assert any("vor dem ersten Test-Commit" in m for m in mangel), mangel


def test_antwortet_die_schnittstelle_mit_fehler_ist_die_pruefung_rot_und_nicht_pruefbar():
    mangel, _ = pa.pruefe_pull_request(12, _Schnittstelle({}, fehler=pa.NichtPruefbar("GitHub antwortet mit 500")))

    assert mangel
    assert all("nicht prüfbar" in m for m in mangel)


def test_unvollstaendige_antwort_ist_nicht_pruefbar_und_nie_gruen():
    antworten = _antworten(_kette(_tests(1, 10), _code(2, 20)))
    antworten["/pulls/12"] = {"number": 12}  # ohne Beschreibung

    mangel, _ = pa.pruefe_pull_request(12, _Schnittstelle(antworten))

    assert mangel
    assert all("nicht prüfbar" in m for m in mangel)


def test_pull_request_den_es_nicht_gibt_ist_nicht_pruefbar():
    mangel, _ = pa.pruefe_pull_request(12, _Schnittstelle({}))

    assert mangel
    assert all("nicht prüfbar" in m for m in mangel)


def test_zweihundertfuenfzig_commits_sind_unvollstaendig_und_damit_nicht_pruefbar():
    # Die Liste der Commits eines Pull Requests endet bei 250; mehr wäre nicht zu sehen.
    commits = [_tests(i, 10) for i in range(1, 251)]
    schnittstelle = _Schnittstelle(_antworten(_kette(*commits)))

    mangel, _ = pa.pruefe_pull_request(12, schnittstelle)

    assert mangel
    assert all("nicht prüfbar" in m for m in mangel)


def test_liste_wird_ueber_alle_seiten_gelesen():
    antworten = {"/pulls/12/commits": [{"nr": i} for i in range(101)]}
    schnittstelle = _Schnittstelle(antworten)

    alle = pa.liste_lesen(schnittstelle, "/pulls/12/commits")

    assert len(alle) == 101
    assert len(schnittstelle.adressen) == 2
    assert "page=2" in schnittstelle.adressen[1]


def test_abstammung_ordnen_stellt_die_aeltesten_commits_nach_vorn():
    a, b, c = (_sha(i) for i in (1, 2, 3))
    commits = [{"sha": c, "parents": [b]}, {"sha": a, "parents": []}, {"sha": b, "parents": [a]}]

    assert [x["sha"] for x in pa.abstammung_ordnen(commits)] == [a, b, c]


def test_bereinige_entfernt_zeilenumbrueche_und_prozentzeichen():
    sauber = pa.bereinige("::error::falsch\r\nzweite Zeile 100%")

    assert "\n" not in sauber
    assert "\r" not in sauber
    assert "%" not in sauber


# --- Der Prüfablauf auf GitHub ----------------------------------------------------------------


def _ablauf():
    return yaml.safe_load(ABLAUF.read_text(encoding="utf-8"))


def _ausloeser(daten):
    # YAML liest das Schlüsselwort „on“ als Wahrheitswert.
    return daten.get("on", daten.get(True))


def test_ablauf_laeuft_beim_oeffnen_bearbeiten_neuen_stand_und_wiedereroeffnen():
    ausloeser = _ausloeser(_ablauf())

    assert set(ausloeser["pull_request"]["types"]) == {"opened", "edited", "synchronize", "reopened"}
    assert set(ausloeser) == {"pull_request"}


def test_ablauf_nutzt_nie_pull_request_target():
    assert "pull_request_target" not in ABLAUF.read_text(encoding="utf-8")


def test_ablauf_hat_nur_leserechte():
    daten = _ablauf()

    assert daten["permissions"] == {"contents": "read", "issues": "read", "pull-requests": "read"}
    assert "permissions" not in daten["jobs"]["angaben"] or daten["jobs"]["angaben"]["permissions"] == daten["permissions"]


def test_ablauf_bricht_aeltere_laeufe_desselben_pull_requests_ab():
    gruppe = _ablauf()["concurrency"]

    assert gruppe["cancel-in-progress"] is True
    assert "github.event.pull_request.number" in gruppe["group"]


def test_ablauf_setzt_keinen_fremden_text_in_einen_befehl_ein():
    for schritt in _ablauf()["jobs"]["angaben"]["steps"]:
        assert "${{" not in schritt.get("run", ""), schritt


def test_ablauf_nutzt_nur_checkout_mit_fester_kennung_und_ohne_gespeicherte_zugangsdaten():
    schritte = _ablauf()["jobs"]["angaben"]["steps"]
    fremde = [s["uses"] for s in schritte if "uses" in s]
    ci_kennung = re.search(r"actions/checkout@([0-9a-f]{40})", CI.read_text(encoding="utf-8")).group(1)

    assert fremde == [f"actions/checkout@{ci_kennung}"]
    checkout = next(s for s in schritte if "uses" in s)
    assert checkout["with"]["persist-credentials"] is False


def test_ablauf_braucht_keine_pakete_und_ruft_das_skript_mit_python_aus_dem_runner_auf():
    befehle = " ".join(s.get("run", "") for s in _ablauf()["jobs"]["angaben"]["steps"])

    assert "python3 .github/pr_angaben.py" in befehle
    for paket in ["pip", "uv ", "npm", "apt"]:
        assert paket not in befehle


def test_ablauf_hat_ein_kurzes_zeitlimit():
    assert _ablauf()["jobs"]["angaben"]["timeout-minutes"] <= 5


def test_der_lange_pruefablauf_startet_beim_bearbeiten_der_beschreibung_nicht():
    ausloeser = _ausloeser(yaml.safe_load(CI.read_text(encoding="utf-8")))

    assert "types" not in (ausloeser["pull_request"] or {})


def test_skript_liest_nur_die_pull_request_nummer_aus_der_ereignisdatei():
    quelltext = SKRIPT.read_text(encoding="utf-8")

    assert "GITHUB_EVENT_PATH" in quelltext
    assert f"https://api.github.com/repos/{REPO}" in quelltext


@pytest.mark.parametrize("fremd", ["http://", "https://example.com", "https://uploads.github.com"])
def test_skript_ruft_nie_eine_adresse_aus_einem_link_ab(fremd):
    antworten = {"/pulls/12": {"number": 12, "body": _beschreibung(davor=f"{fremd}/x"), "updated_at": _zeit(1)}}
    schnittstelle = _Schnittstelle(antworten)

    pa.pruefe_pull_request(12, schnittstelle)

    assert all(adresse.startswith("/") for adresse in schnittstelle.adressen)
