"""Tests für den Ablauf der Prüfung auf GitHub (.github/workflows/ci.yml), Issues #133, #256, #276 und #307.

Das Installieren der Test-Browser hängt manchmal, weil der Ubuntu-Paketserver auf dem
betroffenen Rechner immer langsamer liefert. Entschieden ist (#133, 23.10.2026): abfangen.
Die Browser kommen aus dem Zwischenspeicher von GitHub, und scheitert die Installation, ist
der Lauf rot mit klarer Meldung.

Issue #276 (06.11.2026): Ein zweiter Versuch im selben Lauf half 3 von 7 Mal, ein dritter nie, ein
kompletter Neustart fast immer. Deshalb gibt es nur noch einen Versuch mit 5 Minuten; danach
ist der Lauf rot, und ein Neustart bekommt einen neuen Rechner. Der Schritt „Alle Prüfungen“
behielt damals seine 45 Minuten (#256), der ganze Lauf hatte 55.

Issue #307 (13.11.2026): Die Prüfungen laufen in sechs Teilen gleichzeitig auf eigenen Rechnern
(`./pruefen.sh teil <name>`); nur die drei Teile mit Rauchtest installieren einen Browser, je
ihren eigenen. Jeder Teil läuft zu Ende, auch wenn ein anderer rot ist. Die Gesamtprüfung „Alle
Prüfungen (pruefen.sh)“ ist nur grün, wenn alle Teile grün sind. Die Zeitlimits gelten je Teil;
die Summe wird hier nachgerechnet.

Issue #348 (15.11.2026): Der Pull Request entsteht als Entwurf vor der unabhängigen Prüfung, damit
GitHub gleichzeitig prüft. Das wirkt nur, solange „Prüfungen“ und „PR-Angaben“ auch Entwürfe prüfen,
und der zuletzt geprüfte Stand bleibt nur gültig, solange „bereit“ keinen neuen Lauf startet.

Issue #349 (17.11.2026): Ist ein Rauchtest rot, liegen am Lauf die Aufzeichnung des Browsers und das
Protokoll von Keycloak zum Herunterladen (Belege für die seltenen Hänger beim Anmelden). Die Datenbank
läuft auf GitHub, im Leistungstest und lokal in derselben festen Fassung wie in der Testumgebung.

Issue #396 (20.11.2026): Auch die Systembibliotheken, die jeder Browser unter Linux braucht, kommen in den
Zwischenspeicher, zusammen mit dem Browser in einem Eintrag je Browser, Playwright-Fassung und Stand der
installierten Systempakete des GitHub-Rechners. Ist der Eintrag gefüllt, fragt der Teil den Ubuntu-Paketserver gar nicht an; ist er leer,
installiert er wie bisher und füllt danach den Eintrag. Ob das auf GitHub ohne Paketserver und unter
1 Minute geht, belegt ein Lauf im Pull Request.

Diese Tests sorgen dafür, dass das nicht still aus ci.yml verschwindet. Ob GitHub es
tatsächlich so ausführt, zeigt erst ein Lauf dort.
"""

import re
import subprocess
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CI = BASE_DIR / ".github" / "workflows" / "ci.yml"
PR_ANGABEN = BASE_DIR / ".github" / "workflows" / "pr-angaben.yml"
LEISTUNGSTEST = BASE_DIR / ".github" / "workflows" / "leistungstest.yml"
DEV_COMPOSE = BASE_DIR / "dev" / "docker-compose.yml"
TESTUMGEBUNG_COMPOSE = BASE_DIR / "testumgebung" / "docker-compose.yml"
INSTALL_NAME = "Browser für den Rauchtest installieren"
INSTALL_COMMAND = "uv run --locked playwright install --with-deps ${{ matrix.browser }}"
TEIL_COMMAND = "./pruefen.sh teil ${{ matrix.teil }}"
BROWSER_CONDITION = "matrix.browser"


def _workflow() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def _job() -> dict:
    return _workflow()["jobs"]["pruefen"]


def _gesamt() -> dict:
    return _workflow()["jobs"]["gesamt"]


def _steps() -> list[dict]:
    return _job()["steps"]


def _install_steps() -> list[dict]:
    return [step for step in _steps() if "playwright install" in step.get("run", "")]


def _install() -> dict:
    steps = _install_steps()
    assert len(steps) == 1, [step.get("name") for step in steps]
    return steps[0]


def _tests() -> dict:
    tests = [step for step in _steps() if "./pruefen.sh" in step.get("run", "")]
    assert len(tests) == 1
    return tests[0]


def _teile_aus_dem_skript() -> list[str]:
    done = subprocess.run(  # noqa: S603 -- festes Skript dieses Repos, nur die Liste der Teile
        ["/bin/sh", str(BASE_DIR / "pruefen.sh"), "teile"], capture_output=True, text=True, timeout=30, check=False
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout.split()


def _index(step: dict) -> int:
    return _steps().index(step)


def _condition(step: dict) -> str:
    return " ".join(str(step.get("if", "")).split())


def _restore() -> dict:
    restores = [step for step in _steps() if str(step.get("uses", "")).startswith("actions/cache/restore@")]
    assert len(restores) == 1, [step.get("name") for step in restores]
    return restores[0]


def _save() -> dict:
    saves = [step for step in _steps() if str(step.get("uses", "")).startswith("actions/cache/save@")]
    assert len(saves) == 1, [step.get("name") for step in saves]
    return saves[0]


def _zweige() -> tuple[str, str]:
    """Die beiden Zweige der Installation: Eintrag im Zwischenspeicher gefüllt und leer (#396)."""
    run = _install()["run"]
    kopf = f'if [ "${{{{ steps.{_restore()["id"]}.outputs.cache-hit }}}}" = true ]; then'
    assert run.startswith(kopf + "\n"), run.splitlines()[0]
    gefuellt, rest = run.removeprefix(kopf).split("\nelse\n")
    leer, ende = rest.rsplit("\nfi", 1)
    assert ende.strip() == ""
    return gefuellt, leer


def _befehle(skript: str) -> list[str]:
    """Die Zeilen eines Skripts ohne Kommentare."""
    return [zeile.strip() for zeile in skript.splitlines() if zeile.strip() and not zeile.strip().startswith("#")]


def test_browser_werden_in_genau_einem_schritt_ohne_weitere_versuche_installiert():
    install = _install()

    assert install["name"] == INSTALL_NAME
    # Auch keine Wiederholung innerhalb des Schritts und kein zweiter Aufruf an anderer Stelle.
    befehle = _befehle(install["run"])
    assert not [zeile for zeile in befehle if re.match(r"(for|while|until)\b", zeile)], befehle
    # Bei leerem Zwischenspeicher genau der Aufruf wie bisher, und nur dort (#396).
    assert [zeile for zeile in befehle if "--with-deps" in zeile] == [INSTALL_COMMAND]
    assert "uses" not in install
    # Einzige Bedingung: Der Teil hat einen Browser (#307); sonst gibt es nichts zu installieren.
    assert _condition(install) == BROWSER_CONDITION
    assert [step["name"] for step in _steps() if step.get("name", "").startswith(INSTALL_NAME)] == [INSTALL_NAME]


def test_die_installation_hat_ein_zeitlimit_von_fuenf_minuten():
    assert _install()["timeout-minutes"] == 5


def test_scheitert_die_installation_ist_der_lauf_rot_mit_klarer_meldung():
    install = _install()
    # Die Installation darf nicht selbst den Lauf beenden, sonst käme die Meldung nicht;
    # das übernimmt der nächste Schritt.
    assert install["continue-on-error"] is True
    final = [step for step in _steps() if _condition(step) == f"steps.{install['id']}.outcome == 'failure'"]

    assert len(final) == 1
    step = final[0]
    assert "continue-on-error" not in step
    assert "::error" in step["run"]
    assert "Browser-Installation" in step["run"]
    assert "Kein Test ist gelaufen" in step["run"]
    assert "Neustart" in step["run"]
    # Neu gestartet werden nur die gescheiterten Teile (#307).
    assert "Re-run failed jobs" in step["run"]
    assert step["run"].strip().endswith("exit 1")
    # Die Meldung kommt direkt nach der Installation, bevor ein Test laufen könnte.
    assert _index(install) + 1 == _index(step) < _index(_tests())


def _version_step() -> dict:
    return next(step for step in _steps() if "playwright" in str(step.get("id", "")) and "run" in step)


def test_browser_und_systempakete_kommen_aus_dem_zwischenspeicher_je_browser_playwright_und_paketstand():
    """#396, Nr. 1 und 2: ein Eintrag je Browser, Playwright-Fassung aus uv.lock und Paketstand des GitHub-Rechners."""
    restore = _restore()
    version_step = _version_step()

    # Wie die anderen fremden Bausteine auf eine feste Fassung (Commit) festgelegt; nur actions/cache.
    assert re.fullmatch(r"actions/cache/restore@[0-9a-f]{40}", restore["uses"])
    assert not [step for step in _steps() if str(step.get("uses", "")).startswith("actions/cache@")]
    assert restore["with"]["path"].split() == ["~/.cache/ms-playwright", "~/systempakete"]
    # Der Schlüssel enthält die Playwright-Fassung, die uv aus uv.lock installiert hat.
    assert "--locked" in version_step["run"]
    assert "version('playwright')" in version_step["run"]
    assert f"steps.{version_step['id']}.outputs.version" in restore["with"]["key"]
    # Und der Stand der installierten Systempakete, damit nach einem Update des Rechners keine veralteten
    # Pakete auf einen neueren kommen; gleich bestückte Rechner mit verschiedener Fassungsnummer teilen
    # sich den Eintrag (#396, Nr. 1, Nachklärung vom 20.11.2026).
    assert "$ImageOS" in version_step["run"]
    assert "ImageVersion" not in version_step["run"]
    fingerabdruck = [zeile for zeile in _befehle(version_step["run"]) if "dpkg-query" in zeile]
    assert len(fingerabdruck) == 1, version_step["run"]
    assert "${Version}" in fingerabdruck[0] and "sha256sum" in fingerabdruck[0]
    assert f"steps.{version_step['id']}.outputs.abbild" in restore["with"]["key"]
    # Je Browser ein eigener Eintrag, weil jeder Teil nur seinen Browser installiert (#307).
    assert "${{ matrix.browser }}" in restore["with"]["key"]
    # Nur der genau passende Eintrag, nie ein ähnlicher mit anderer Fassung.
    assert "restore-keys" not in restore["with"]
    assert _condition(restore) == _condition(version_step) == BROWSER_CONDITION
    sync = next(step for step in _steps() if step.get("run") == "uv sync --locked")
    assert _index(sync) < _index(version_step) < _index(restore) < _index(_install())


def test_mit_gefuelltem_zwischenspeicher_fragt_der_teil_den_paketserver_nicht_an():
    """#396, Nr. 1: kein Aufruf, der den Ubuntu-Paketserver anfragt, auch nicht für die Paketlisten."""
    gefuellt, _ = _zweige()
    befehle = _befehle(gefuellt)
    installieren = [zeile for zeile in befehle if "apt-get install" in zeile]

    assert len(installieren) == 1, befehle
    assert "--no-download" in installieren[0]
    assert '"$HOME/systempakete"/*.deb' in installieren[0]
    for verboten in ("--with-deps", "install-deps", "apt-get download"):
        assert not [zeile for zeile in befehle if verboten in zeile], (verboten, befehle)
    # Auch keine Paketlisten, in keiner Schreibweise (Befund B2 der unabhängigen Prüfung).
    assert not [zeile for zeile in befehle if re.search(r"\bapt(-get)?\b.*\bupdate\b", zeile)], befehle
    # Scheitert die Installation aus dem Zwischenspeicher, ist der Teil rot, statt still weiterzumachen.
    assert not [zeile for zeile in befehle if "||" in zeile], befehle
    # Der Browser in genau der Fassung zu Playwright aus uv.lock (#396, Nr. 2); ist er schon da, lädt das nichts.
    assert "uv run --locked playwright install ${{ matrix.browser }}" in befehle


def test_mit_leerem_zwischenspeicher_installiert_der_teil_wie_bisher_und_behaelt_die_pakete():
    """#396, Nr. 3: wie heute vom Paketserver; apt legt die geladenen Pakete für den Zwischenspeicher ab."""
    _, leer = _zweige()
    befehle = _befehle(leer)
    installieren = befehle.index(INSTALL_COMMAND)
    einstellung = [i for i, zeile in enumerate(befehle) if "Dir::Cache::Archives" in zeile]
    kopieren = [i for i, zeile in enumerate(befehle) if "$HOME/systempakete" in zeile and ".deb" in zeile]

    assert len(einstellung) == 1 and einstellung[0] < installieren, befehle
    assert "Keep-Downloaded-Packages" in befehle[einstellung[0]]
    assert len(kopieren) == 1 and installieren < kopieren[0], befehle
    # Ein gescheitertes Kopieren macht den Schritt rot, statt einen unvollständigen Eintrag zu speichern
    # (Befund V1 der unabhängigen Prüfung): „-exec … +“ gibt den Fehler weiter, „-exec … \;“ nicht.
    assert befehle[kopieren[0]].endswith("+"), befehle[kopieren[0]]


def test_der_eintrag_wird_gleich_nach_erfolgreicher_installation_gefuellt():
    """#396, Nr. 3: Ist der Eintrag leer, füllt ihn der Teil, sobald die Installation geklappt hat."""
    restore, save, install = _restore(), _save(), _install()

    assert save["uses"].split("@")[1] == restore["uses"].split("@")[1]
    assert save["with"]["path"] == restore["with"]["path"]
    assert save["with"]["key"] == f"${{{{ steps.{restore['id']}.outputs.cache-primary-key }}}}"
    assert _condition(save) == (
        f"{BROWSER_CONDITION} && steps.{install['id']}.outcome == 'success' "
        f"&& steps.{restore['id']}.outputs.cache-hit != 'true'"
    )
    # Direkt nach der Meldung zur gescheiterten Installation, vor den Prüfungen: Auch ein roter Test
    # lässt den Eintrag gefüllt zurück.
    assert _index(install) + 2 == _index(save) < _index(_tests())


# Fester Rest je Teil außer Installation und Prüfungen (#276): Vorlauf bis zur Installation bis
# gut 1 Minute (Container, Keycloak starten, Zwischenspeicher; Lauf 41899114419: 41 Sekunden),
# Warten auf Keycloak höchstens 3 Minuten (90 Versuche à 2 Sekunden), Aufräumen und Hochladen des
# Ergebnisses wenige Sekunden. Hängt die Installation, endet der Teil nach ihren 5 Minuten rot,
# ohne dass Prüfungen laufen; die Summe muss also nur für eine erfolgreiche Installation und die
# Prüfungen reichen. Vor #307 brauchten alle Prüfungen nacheinander höchstens knapp 34 Minuten,
# davon der Rauchtest in allen drei Browsern rund 19 und die übrigen Tests rund 9.
REST_MINUTEN = 5


def test_der_schritt_mit_den_pruefungen_eines_teils_hat_ein_eigenes_zeitlimit_von_25_minuten():
    assert _tests()["timeout-minutes"] == 25


def test_jeder_teil_hat_ein_zeitlimit_von_35_minuten():
    assert _job()["timeout-minutes"] == 35


def test_installation_pruefungen_und_rest_passen_ins_zeitlimit_eines_teils():
    summe = _install()["timeout-minutes"] + _tests()["timeout-minutes"] + REST_MINUTEN

    assert summe <= _job()["timeout-minutes"]


# --- Teile gleichzeitig auf eigenen Rechnern (#307) ---------------------------------------------


def test_die_teile_auf_github_sind_genau_die_teile_aus_pruefen_sh():
    matrix = _job()["strategy"]["matrix"]

    assert set(matrix) == {"include"}, "nur die Liste der Teile, keine weiteren Kombinationen"
    assert [eintrag["teil"] for eintrag in matrix["include"]] == _teile_aus_dem_skript()


def test_nur_die_teile_mit_rauchtest_haben_einen_browser_und_zwar_ihren_eigenen():
    for eintrag in _job()["strategy"]["matrix"]["include"]:
        teil = eintrag["teil"]
        if teil.startswith("rauchtest-"):
            assert eintrag == {"teil": teil, "browser": teil.removeprefix("rauchtest-")}
        else:
            assert eintrag == {"teil": teil}


def test_jeder_teil_laeuft_zu_ende_auch_wenn_ein_anderer_rot_ist():
    strategy = _job()["strategy"]

    assert strategy["fail-fast"] is False
    assert "max-parallel" not in strategy
    assert "continue-on-error" not in _job()


def test_jeder_teil_ruft_pruefen_sh_mit_seinem_namen_auf():
    tests = _tests()

    assert tests["run"].strip() == TEIL_COMMAND
    assert "if" not in tests
    assert "continue-on-error" not in tests
    assert "matrix.teil" in _job()["name"]


def test_jeder_teil_laedt_sein_ergebnis_hoch_auch_wenn_er_rot_ist():
    tests = _tests()
    ergebnis = tests["env"]["PRUEFTEIL_ERGEBNIS"]
    # Seit #349 lädt ein Teil mit rotem Rauchtest auch Belege hoch (Test weiter unten); hier zählt nur das Ergebnis.
    uploads = [
        step
        for step in _steps()
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
        and not str(step["with"]["name"]).startswith("belege-")
    ]

    assert len(uploads) == 1
    upload = uploads[0]
    assert re.fullmatch(r"actions/upload-artifact@[0-9a-f]{40}", upload["uses"])
    assert _condition(upload) == "always()"
    assert upload["with"]["path"] == ergebnis
    assert "${{ matrix.teil }}" in ergebnis and "${{ runner.temp }}" in ergebnis
    assert upload["with"]["name"] == "ergebnis-${{ matrix.teil }}"
    # Beim Neustart gescheiterter Teile ersetzt das neue Ergebnis das alte.
    assert upload["with"]["overwrite"] is True
    assert _index(tests) < _index(upload)


def test_die_gesamtpruefung_wartet_auf_alle_teile_und_laeuft_immer():
    gesamt = _gesamt()

    assert gesamt["name"] == "Alle Prüfungen (pruefen.sh)"
    assert gesamt["needs"] == "pruefen"
    assert _condition(gesamt) == "always()"
    assert set(_workflow()["jobs"]) == {"pruefen", "gesamt"}


def test_die_gesamtpruefung_fasst_die_ergebnisse_aller_teile_mit_pruefen_sh_zusammen():
    steps = _gesamt()["steps"]
    downloads = [step for step in steps if "gh run download" in step.get("run", "")]
    gesamt = [step for step in steps if "./pruefen.sh gesamt" in step.get("run", "")]

    assert len(downloads) == 1 and len(gesamt) == 1
    download, zusammenfassen = downloads[0], gesamt[0]
    # Über die Schnittstelle von GitHub für den ganzen Lauf, nicht über actions/download-artifact:
    # Nach „Re-run failed jobs“ müssen auch die Ergebnisse der grünen Teile aus dem ersten Versuch
    # da sein (Befund M1 der unabhängigen Prüfung).
    assert not [step for step in steps if "download-artifact" in str(step.get("uses", ""))]
    assert '"$GITHUB_RUN_ID"' in download["run"]
    assert "--pattern 'ergebnis-*'" in download["run"]
    assert download["env"]["GH_TOKEN"] == "${{ github.token }}"  # noqa: S105 -- Verweis auf den Schlüssel des Laufs, kein Passwort
    assert _gesamt()["permissions"] == {"actions": "read", "contents": "read"}
    assert zusammenfassen["run"].strip() == './pruefen.sh gesamt "$RUNNER_TEMP/ergebnisse"'
    assert '"$RUNNER_TEMP/ergebnisse"' in download["run"]
    assert steps.index(download) < steps.index(zusammenfassen)
    assert "continue-on-error" not in zusammenfassen


def test_die_gesamtpruefung_ist_rot_wenn_ein_teil_nicht_gruen_beendet_ist():
    steps = _gesamt()["steps"]
    pruefung = [step for step in steps if "needs.pruefen.result" in _condition(step)]

    assert len(pruefung) == 1
    step = pruefung[0]
    # Läuft auch, wenn die Zusammenfassung schon rot war, und nur, wenn nicht alle Teile grün sind:
    # abgebrochen, übersprungen oder rot.
    assert _condition(step) == "always() && needs.pruefen.result != 'success'"
    assert "::error" in step["run"]
    assert step["run"].strip().endswith("exit 1")
    assert "continue-on-error" not in step


def test_die_gesamtpruefung_hat_ein_kurzes_zeitlimit():
    assert _gesamt()["timeout-minutes"] <= 5


# ---------- Pull Request als Entwurf (#348) ----------

# Ohne eigene Liste startet GitHub einen Lauf bei diesen Ereignissen eines Pull Requests.
STANDARD_EREIGNISSE = ["opened", "synchronize", "reopened"]


def _ereignisse(pfad: Path) -> list[str]:
    workflow = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    ausloeser = workflow.get("on", workflow.get(True))  # YAML liest das Wort „on“ als wahr
    return (ausloeser["pull_request"] or {}).get("types", STANDARD_EREIGNISSE)


def _bedingungen(pfad: Path) -> list[str]:
    jobs = yaml.safe_load(pfad.read_text(encoding="utf-8"))["jobs"].values()
    teile = [*jobs, *(step for job in jobs for step in job.get("steps", []))]
    return [str(teil["if"]) for teil in teile if "if" in teil]


def test_ein_entwurf_wird_beim_anlegen_und_bei_jedem_neuen_stand_geprueft():
    """S1 und S3: Auf GitHub laufen „Prüfungen“ und „PR-Angaben“ schon für den Entwurf."""
    for pfad in (CI, PR_ANGABEN):
        ereignisse = _ereignisse(pfad)
        assert {"opened", "synchronize"} <= set(ereignisse), (pfad.name, ereignisse)
        assert not [b for b in _bedingungen(pfad) if "draft" in b], f"{pfad.name} überspringt Entwürfe"


def test_bereit_stellen_startet_keinen_neuen_lauf():
    """S4: Der zuletzt geprüfte Stand bleibt gültig, wenn die KI den Entwurf auf „bereit“ stellt."""
    for pfad in (CI, PR_ANGABEN):
        assert "ready_for_review" not in _ereignisse(pfad), pfad.name


def _yaml(pfad: Path) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def test_datenbank_ueberall_in_derselben_festen_fassung_wie_die_testumgebung():
    """#349: Auf GitHub, im Leistungstest und lokal läuft dieselbe PostgreSQL-Fassung wie in der Testumgebung."""
    fest = _yaml(TESTUMGEBUNG_COMPOSE)["services"]["datenbank"]["image"]
    gefunden = {
        "ci.yml": _job()["services"]["postgres"]["image"],
        "leistungstest.yml": _yaml(LEISTUNGSTEST)["jobs"]["messen"]["services"]["postgres"]["image"],
        "dev/docker-compose.yml": _yaml(DEV_COMPOSE)["services"]["postgres"]["image"],
    }

    assert re.fullmatch(r"postgres:18\.\d+@sha256:[0-9a-f]{64}", fest), fest
    assert gefunden == dict.fromkeys(gefunden, fest)


BELEGE = "${{ runner.temp }}/belege"
BELEGE_BEDINGUNG = "failure() && steps.pruefen.outcome == 'failure' && matrix.browser"


def _belege_schritte() -> tuple[dict, dict]:
    """Die Schritte nach den Prüfungen eines Teils, die das Protokoll von Keycloak sichern und die Belege hochladen."""
    nachher = _steps()[_index(_tests()) + 1 :]
    keycloak = [step for step in nachher if "docker logs keycloak" in step.get("run", "")]
    hochladen = [step for step in nachher if str(step.get("with", {}).get("name", "")).startswith("belege-")]
    assert len(keycloak) == 1 and len(hochladen) == 1, [step.get("name") for step in nachher]
    return keycloak[0], hochladen[0]


def test_rauchtests_zeichnen_auf_github_fuer_rote_tests_auf():
    """#349: Auf GitHub bekommen die Rauchtests einen Ablageort; dorthin kommt die Aufzeichnung jedes roten Tests.

    Was dort landet und dass grüne Tests nichts ablegen, prüft rauchtests/test_aufzeichnung.py.
    """
    tests = _tests()

    assert tests["id"] == "pruefen"
    assert tests["env"]["RAUCHTEST_SPUREN"] == BELEGE


def test_ist_ein_rauchtest_rot_liegen_aufzeichnung_und_keycloak_protokoll_zum_herunterladen():
    """#349: Nur wenn die Prüfungen eines Teils mit Browser rot sind, kommen Aufzeichnungen und Keycloak-Protokoll an den Lauf."""
    keycloak, hochladen = _belege_schritte()

    assert _condition(keycloak) == BELEGE_BEDINGUNG
    assert '"$RUNNER_TEMP/belege/keycloak.log"' in keycloak["run"]
    assert _index(keycloak) < _index(hochladen)
    assert _condition(hochladen) == BELEGE_BEDINGUNG
    assert re.fullmatch(r"actions/upload-artifact@[0-9a-f]{40}", hochladen["uses"])
    assert hochladen["with"]["path"] == BELEGE
    # Je Versuch ein eigener Name: Nach einem Neustart bleiben die Belege des ersten Versuchs erhalten.
    assert hochladen["with"]["name"] == "belege-${{ matrix.teil }}-versuch-${{ github.run_attempt }}"
    assert "overwrite" not in hochladen["with"]
