"""Tests für den Ablauf „Abbild veröffentlichen“ (.github/workflows/abbild-veroeffentlichen.yml), #302.

Nach jedem grünen Stand von main baut GitHub das Abbild des Tools für den ARM64-Server des DPV und legt es
mit einer Kennung je Stand in der GitHub Container Registry ab; der Server holt es von dort (Grundlage:
Pull Request #404 des DPV-Admins). Ein roter Stand, ein Pull Request, ein anderer Branch oder ein Fork
veröffentlicht nichts, und GitHub bekommt keinen Zugang zum Server.

Szenarien: keine (#302, Klärung vom 23.11.2026); diese Tests halten die Akzeptanzkriterien technisch fest.
Ob GitHub den Ablauf tatsächlich so ausführt, zeigt erst der erste Lauf nach dem Übernehmen.
"""

import re
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
WORKFLOWS = BASE_DIR / ".github" / "workflows"
ABLAUF = WORKFLOWS / "abbild-veroeffentlichen.yml"
CI = WORKFLOWS / "ci.yml"


def _yaml(pfad: Path) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def _ablauf() -> dict:
    return _yaml(ABLAUF)


def _ausloeser(workflow: dict) -> dict:
    return workflow.get("on", workflow.get(True))  # YAML liest das Wort „on“ als wahr


def _job() -> dict:
    jobs = _ablauf()["jobs"]
    assert list(jobs) == ["bauen"], list(jobs)
    return jobs["bauen"]


def _steps() -> list[dict]:
    return _job()["steps"]


def _schritt(baustein: str) -> dict:
    treffer = [step for step in _steps() if str(step.get("uses", "")).startswith(f"{baustein}@")]
    assert len(treffer) == 1, [step.get("uses") for step in _steps()]
    return treffer[0]


def _bedingung(teil: dict) -> str:
    return " ".join(str(teil.get("if", "")).split())


def test_nur_ein_beendeter_lauf_der_pruefungen_auf_main_loest_den_ablauf_aus():
    """Kein Pull Request, kein Push und kein Start von Hand: nur das Ende der „Prüfungen“ auf main."""
    ausloeser = _ausloeser(_ablauf())

    assert list(ausloeser) == ["workflow_run"]
    lauf = ausloeser["workflow_run"]
    # Genau der Name aus ci.yml; ein Tippfehler hier hieße, der Ablauf startet nie.
    assert lauf["workflows"] == [_yaml(CI)["name"]]
    assert lauf["types"] == ["completed"]
    assert lauf["branches"] == ["main"]


def test_ein_roter_stand_ein_pull_request_oder_ein_anderer_branch_veroeffentlicht_nichts():
    """Gebaut wird nur nach grünen Prüfungen eines Pushs auf main; ein Pull Request, auch aus einem Fork, nie."""
    bedingung = _bedingung(_job())
    teile = [teil.strip() for teil in bedingung.split("&&")]

    assert "github.event.workflow_run.conclusion == 'success'" in teile
    assert "github.event.workflow_run.event == 'push'" in teile
    assert "github.event.workflow_run.head_branch == 'main'" in teile
    assert "||" not in bedingung


def test_ein_neu_gestarteter_lauf_fuer_einen_aelteren_stand_veroeffentlicht_nichts():
    """Wird „Prüfungen“ für einen älteren Stand von main neu gestartet und grün, rollte der Server sonst zurück.

    Bei diesem Auslöser ist `github.sha` der neueste Stand von main; nur wenn der geprüfte Stand genau
    der ist, wird gebaut.
    """
    teile = [teil.strip() for teil in _bedingung(_job()).split("&&")]

    assert "github.event.workflow_run.head_sha == github.sha" in teile


def test_gebaut_wird_genau_der_gepruefte_commit():
    checkout = _schritt("actions/checkout")

    assert checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"
    # Der Zugang zum Repo bleibt nicht im Arbeitsordner liegen, aus dem das Abbild gebaut wird.
    assert checkout["with"]["persist-credentials"] is False
    assert _steps().index(checkout) == 0


def test_das_abbild_wird_fuer_arm64_gebaut_und_in_die_github_container_registry_gelegt():
    """Der Server des DPV ist ARM64 (#222); gebaut wird auf einem ARM-Rechner von GitHub, ohne Nachbilden."""
    assert _job()["runs-on"] == "ubuntu-24.04-arm"
    bauen = _schritt("docker/build-push-action")

    assert bauen["with"]["platforms"] == "linux/arm64"
    assert bauen["with"]["push"] is True
    assert bauen["with"]["context"] == "."
    assert _ablauf()["env"]["ABBILD"] == "ghcr.io/${{ github.repository }}"
    assert _schritt("docker/login-action")["with"]["registry"] == "ghcr.io"
    assert _schritt("docker/metadata-action")["with"]["images"] == "${{ env.ABBILD }}"


def test_jeder_stand_bekommt_eine_eigene_kennung_und_latest_zeigt_auf_den_neuesten():
    """Der Server startet immer eine feste Version, nie „latest“; „latest“ zeigt ihm nur, welche die neueste ist."""
    version = next(step for step in _steps() if step.get("id") == "version")
    meta = _schritt("docker/metadata-action")
    tags = [zeile.strip() for zeile in meta["with"]["tags"].splitlines() if zeile.strip()]

    # Datum und Laufnummer dieses Ablaufs: eindeutig und aufsteigend.
    assert "date -u +%Y.%m.%d" in version["run"]
    assert "${{ github.run_number }}" in version["run"]
    assert "type=raw,value=${{ steps.version.outputs.version }}" in tags
    # Dazu der Commit, damit sich nachsehen lässt, welcher Stand in welcher Version steckt.
    assert "type=sha,format=long" in tags
    assert "type=raw,value=latest" in tags
    assert len(tags) == 3, tags
    # Die Version steht im Abbild selbst; daran liest der Server ab, welche Version „latest“ ist.
    assert "org.opencontainers.image.version=${{ steps.version.outputs.version }}" in meta["with"]["labels"]
    bauen = _schritt("docker/build-push-action")
    assert bauen["with"]["tags"] == "${{ steps.meta.outputs.tags }}"
    assert bauen["with"]["labels"] == "${{ steps.meta.outputs.labels }}"
    # Ein einziges Abbild ohne zusätzlichen Beglaubigungs-Eintrag, wie der Server es erwartet.
    assert bauen["with"]["provenance"] is False


def test_ein_laufender_ablauf_wird_nie_abgebrochen():
    """Ein halb hochgeladenes Abbild wäre schlimmer als ein wartender Lauf; zwei Merges laufen nacheinander."""
    concurrency = _ablauf()["concurrency"]

    assert concurrency["cancel-in-progress"] is False
    assert "${{" not in concurrency["group"]
    assert _job()["timeout-minutes"] <= 30


def test_der_bau_legt_keinen_zwischenspeicher_bei_github_an():
    """Der Zwischenspeicher von GitHub ist je Repo begrenzt; ein Bau-Zwischenspeicher würde die Browser
    der Prüfungen (#396) daraus verdrängen, und die hängen dann wieder am Ubuntu-Paketserver."""
    bauen = _schritt("docker/build-push-action")

    assert "cache-from" not in bauen["with"]
    assert "cache-to" not in bauen["with"]
    assert not [step for step in _steps() if str(step.get("uses", "")).startswith("actions/cache")]


def test_nur_dieser_ablauf_darf_ins_paketverzeichnis_schreiben():
    """Der Ablauf selbst hat nur Leserechte; Schreibrecht für Pakete bekommt nur der eine Teil, der hochlädt."""
    assert _ablauf()["permissions"] == {"contents": "read"}
    assert _job()["permissions"] == {"contents": "read", "packages": "write"}
    for pfad in sorted(WORKFLOWS.glob("*.yml")):
        if pfad == ABLAUF:
            continue
        workflow = _yaml(pfad)
        rechte = [workflow.get("permissions", {}), *(job.get("permissions", {}) for job in workflow["jobs"].values())]
        assert not [r for r in rechte if "packages" in r], pfad.name


def test_github_bekommt_keinen_zugang_zum_server():
    """Der einzige Zugang im Ablauf ist der, den GitHub selbst für jeden Lauf vergibt; kein Geheimnis für den Server."""
    text = ABLAUF.read_text(encoding="utf-8")

    assert re.findall(r"secrets\.\w+", text) == ["secrets.GITHUB_TOKEN"]
    assert "vars." not in text
    befehle = " ".join(str(step.get("run", "")) for step in _steps())
    assert not re.search(r"\b(ssh|scp|rsync|az|curl|wget)\b", befehle), befehle


def test_fremde_bausteine_in_jedem_ablauf_sind_auf_einen_festen_commit_festgelegt():
    """`docs/entscheidungen.md`, 21.10.2026: ein Versionsname ließe sich im fremden Repo still verschieben."""
    for pfad in sorted(WORKFLOWS.glob("*.yml")):
        for job in _yaml(pfad)["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step:
                    assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", step["uses"]), (pfad.name, step["uses"])
