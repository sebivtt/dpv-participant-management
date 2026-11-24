"""Wächter (#402): Kein Rauchtest fragt nur einmal ab, ob ein Dialog modal ist.

Der Dialog kommt offen vom Server und ist damit schon sichtbar; modal macht ihn erst das Skript, das mit
`defer` lädt. Eine einmalige Abfrage direkt nach „sichtbar“ ist deshalb in einem langsamen Browser
manchmal noch `False` (Firefox auf GitHub, Lauf 44738211679). Die Rauchtests warten dafür mit
`expect_modal()` aus rauchtests/conftest.py bis zum üblichen Zeitlimit. Dieser Test liest alle Dateien
unter rauchtests/ und meldet jeden Aufruf, der `:modal` anders als wartend abfragt, mit Datei und Zeile.
"""

import ast
from pathlib import Path

RAUCHTESTS = Path(__file__).resolve().parent.parent / "rauchtests"

# Nur diese Aufrufe warten, bis die Bedingung gilt; alle anderen fragen genau einmal.
WAITING = {"wait_for_function"}


def _single_queries(source: str) -> list[int]:
    """Zeilen von Aufrufen, die `:modal` als Text mitgeben und dabei nicht warten."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        if name in WAITING:
            continue
        texts = [a.value for a in [*node.args, *(k.value for k in node.keywords)]
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if any(":modal" in text for text in texts):
            found.append(node.lineno)
    return found


def _report() -> list[str]:
    return [f"{path.relative_to(RAUCHTESTS.parent)}:{line}"
            for path in sorted(RAUCHTESTS.rglob("*.py"))
            for line in _single_queries(path.read_text(encoding="utf-8"))]


def test_kein_rauchtest_fragt_nur_einmal_ob_ein_dialog_modal_ist():
    found = _report()
    assert found == [], (
        "Diese Stellen fragen nur einmal, ob ein Dialog modal ist; bitte expect_modal() aus "
        "rauchtests/conftest.py nehmen (#402):\n" + "\n".join(found)
    )


def test_der_waechter_erkennt_die_einmalige_abfrage():
    """Gegenprobe: Der Wächter findet die alte Form, auch über mehrere Zeilen, und lässt das Warten durch."""
    source = (
        "dialog.evaluate(\"d => d.matches(':modal')\")\n"
        "page.evaluate(\n    \"() => document.querySelector('dialog').matches(':modal')\",\n)\n"
        "page.wait_for_function(\"d => d.matches(':modal')\", arg=handle)\n"
        "page.locator('dialog:modal').count()\n"
    )
    assert _single_queries(source) == [1, 2, 6]
