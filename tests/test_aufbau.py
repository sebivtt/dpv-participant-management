"""Strukturtest: Der Code folgt der Richtung der Schichten aus docs/aufbau.md (#282).

Die Zuordnung der Dateien zu den Schichten steht nur in docs/aufbau.md, Tabelle „Schichten“;
dieser Test liest sie von dort. Er meldet jeden Import des Tools, der in eine höhere Schicht
zeigt (auch innerhalb von Funktionen), jede Datei ohne Schicht und jeden Pfad in docs/aufbau.md,
den es nicht gibt. Jede Meldung nennt Datei, Zeile und docs/aufbau.md.
"""

import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUFBAU = ROOT / "docs" / "aufbau.md"
HINWEIS = "Regeln und Zuordnung: docs/aufbau.md, Abschnitt „Schichten“."


def _tracked() -> list[str]:
    befehl = ["git", "ls-files"]
    return subprocess.run(befehl, cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()  # noqa: S603 -- fester Befehl


def _backticks(text: str) -> list[str]:
    return re.findall(r"`([^`\n]+)`", text)


def _layers() -> tuple[dict[int, tuple[str, list[str]]], list[str]]:
    """Schichten (Nummer → Name und Pfade) und die ausgenommenen Angaben aus docs/aufbau.md."""
    text = AUFBAU.read_text(encoding="utf-8")
    abschnitt = text.split("## Schichten", 1)[1].split("\n## ", 1)[0]
    schichten = {}
    for nummer, name, dateien in re.findall(r"^\| (\d+) \| ([^|]+) \|[^|]*\| ([^|]+) \|$", abschnitt, flags=re.M):
        schichten[int(nummer)] = (name.strip(), _backticks(dateien))
    ausgenommen = re.search(r"^\*\*Nicht Teil der Schichten:\*\*(.*)$", abschnitt, flags=re.M)
    return schichten, _backticks(ausgenommen.group(1)) if ausgenommen else []


def _excluded(path: str, ausgenommen: list[str]) -> bool:
    teile = path.split("/")
    for angabe in ausgenommen:
        if "/" in angabe:
            if path.startswith(angabe):
                return True
        elif angabe in teile[:-1] or angabe == teile[-1]:
            return True
    return False


def _tool_files() -> list[str]:
    _, ausgenommen = _layers()
    return [p for p in _tracked() if p.endswith(".py") and not _excluded(p, ausgenommen)]


def _layer_of(path: str, schichten) -> list[int]:
    return [
        nummer
        for nummer, (_, pfade) in schichten.items()
        for pfad in pfade
        if path == pfad or (pfad.endswith("/") and path.startswith(pfad))
    ]


def _module_file(module: str, tracked: set[str]) -> str | None:
    """Die Datei des Tools zu einem Modulnamen wie „units.texts“; None, wenn es keine ist."""
    teile = module.split(".")
    while teile:
        basis = "/".join(teile)
        for kandidat in (f"{basis}.py", f"{basis}/__init__.py"):
            if kandidat in tracked:
                return kandidat
        teile.pop()
    return None


def _imports(path: str, tracked: set[str]):
    """(Zeile, Modul, Datei) für jeden Import einer Datei des Tools, auch in Funktionen."""
    baum = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
    paket = path.rsplit("/", 1)[0].replace("/", ".") if "/" in path else ""
    for knoten in ast.walk(baum):
        module = []
        if isinstance(knoten, ast.Import):
            module = [alias.name for alias in knoten.names]
        elif isinstance(knoten, ast.ImportFrom):
            basis = knoten.module or ""
            if knoten.level:
                oben = paket.split(".")[: len(paket.split(".")) - (knoten.level - 1)]
                basis = ".".join([*oben, basis] if basis else oben)
            # „from units import texts“ bindet die Datei units/texts.py ein, nicht units/__init__.py.
            module = [f"{basis}.{alias.name}" for alias in knoten.names] or [basis]
        for modul in module:
            datei = _module_file(modul, tracked)
            if datei:
                yield knoten.lineno, modul, datei


def test_kein_import_zeigt_in_eine_hoehere_schicht():
    schichten, _ = _layers()
    tracked = set(_tracked())
    gezaehlt, falsch = 0, []
    for path in _tool_files():
        eigene = _layer_of(path, schichten)
        for zeile, modul, ziel in _imports(path, tracked):
            gezaehlt += 1
            if path.endswith("__init__.py"):
                falsch.append(f"{path}:{zeile} bindet {modul} ein; eine __init__.py gehört zu keiner Schicht.")
                continue
            if len(eigene) != 1:
                continue  # meldet test_jede_datei_des_tools_hat_genau_eine_schicht
            ziele = _layer_of(ziel, schichten)
            if len(ziele) == 1 and ziele[0] > eigene[0]:
                falsch.append(
                    f"{path}:{zeile} (Schicht {eigene[0]} „{schichten[eigene[0]][0]}“) bindet {modul} ein "
                    f"(Schicht {ziele[0]} „{schichten[ziele[0]][0]}“)."
                )
    # Schutz gegen einen Test, der nichts mehr findet und deshalb immer grün ist.
    assert len(schichten) == 5 and gezaehlt > 50, f"{len(schichten)} Schichten, {gezaehlt} Importe gelesen. {HINWEIS}"
    assert not falsch, "Diese Importe zeigen in eine höhere Schicht:\n" + "\n".join(falsch) + f"\n{HINWEIS}"


def test_jede_datei_des_tools_hat_genau_eine_schicht():
    schichten, _ = _layers()
    ohne, doppelt = [], []
    for path in _tool_files():
        if path.endswith("__init__.py"):
            continue
        treffer = _layer_of(path, schichten)
        if not treffer:
            ohne.append(f"{path}:1")
        elif len(treffer) > 1:
            doppelt.append(f"{path}:1 (Schichten {treffer})")
    assert len(_tool_files()) > 30, f"Nur {len(_tool_files())} Dateien des Tools gefunden. {HINWEIS}"
    assert not ohne, "Diese Dateien haben keine Schicht:\n" + "\n".join(ohne) + f"\n{HINWEIS}"
    assert not doppelt, "Diese Dateien stehen in mehr als einer Schicht:\n" + "\n".join(doppelt) + f"\n{HINWEIS}"


# Wie in tests/test_arbeitsregeln.py: Als Pfad gilt eine Angabe in Backticks mit „/“ oder einer dieser Endungen.
DATEIENDUNGEN = {".md", ".py", ".html", ".css", ".js", ".svg"}


def test_jeder_pfad_in_aufbau_md_existiert():
    tracked = _tracked()
    vorhanden = set(tracked) | {"/".join(p.split("/")[: i + 1]) + "/" for p in tracked for i in range(p.count("/"))}
    namen = {teil for p in tracked for teil in p.split("/")}
    ausgenommen = _layers()[1]
    geprueft, fehlt = 0, []
    for nummer, zeile in enumerate(AUFBAU.read_text(encoding="utf-8").splitlines(), start=1):
        for angabe in _backticks(zeile):
            if re.search(r"[\s<*…]", angabe) or angabe.startswith(("/", "http", "@")):
                continue
            if "/" in angabe.rstrip("/"):
                geprueft += 1
                if angabe not in vorhanden:
                    fehlt.append(f"docs/aufbau.md:{nummer}: `{angabe}`")
            elif angabe.endswith("/") or Path(angabe).suffix in DATEIENDUNGEN or angabe in ausgenommen:
                geprueft += 1
                if angabe.rstrip("/") not in namen:
                    fehlt.append(f"docs/aufbau.md:{nummer}: `{angabe}`")
    assert geprueft > 30, f"Nur {geprueft} Pfade in docs/aufbau.md gelesen."
    assert not fehlt, "Diese Pfade in docs/aufbau.md gibt es nicht:\n" + "\n".join(fehlt)
