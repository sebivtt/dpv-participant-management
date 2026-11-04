"""Helfer für die Vorschau einer sichtbaren Änderung (Skill `vorschau`, #249).

Aus fertig gerenderten Seiten (Antworten des Test-Clients mit erfundenen Daten) entsteht eine
einzelne HTML-Datei, die man ohne Server im Browser öffnet: Gestaltung und Skript sind
eingebettet, Links und Formulare gesperrt, und jeder Fall steht in PC- und in Handybreite da.
Lädt eine Seite eine statische Datei, die der Helfer nicht einbetten kann, bricht er ab; so
bleibt die Vorschau nie still ungestaltet, wenn sich `core/templates/base.html` ändert.
"""

import html
import re
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders

HANDY_BREITE = 390
PC_BREITE = 1200
RAHMEN_HOEHE = 900

_STYLESHEET = re.compile(r"""<link\b[^>]*>""", re.IGNORECASE)
_SCRIPT = re.compile(r"""<script\b[^>]*\bsrc=["'](?P<pfad>[^"']+)["'][^>]*>\s*</script>""", re.IGNORECASE)
_RESTLICHE_STATISCHE_DATEI = re.compile(r"""/static/[^\s"'<>)]*""")

# Sperrt alles, was die Seite verlassen oder etwas speichern würde. Läuft am Ende jeder Seite.
_SPERRE = """<script>
document.addEventListener("click", function (e) {
  if (e.target.closest && e.target.closest("a[href], button[type=submit], input[type=submit]")) { e.preventDefault(); }
}, true);
document.addEventListener("submit", function (e) { e.preventDefault(); }, true);
</script>"""

_STIL = """
body { margin: 0; font-family: system-ui, sans-serif; background: #eef0f3; color: #1b2532; }
header { position: sticky; top: 0; z-index: 2; background: #fff; border-bottom: 1px solid #c9d1db; padding: 10px 16px; }
h1 { font-size: 1.1rem; margin: 0 0 8px; }
nav { display: flex; flex-wrap: wrap; gap: 6px; }
nav button { font: inherit; padding: 6px 12px; border: 1px solid #1a4b7e; background: #fff; color: #1a4b7e; border-radius: 6px; cursor: pointer; }
nav button[aria-pressed=true] { background: #1a4b7e; color: #fff; }
p.hinweis { margin: 8px 0 0; font-size: .85rem; color: #566375; }
main { padding: 16px; }
.fall { display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }
.fall[hidden] { display: none; }
.ansicht h2 { font-size: .95rem; margin: 0 0 6px; }
.ansicht iframe { border: 1px solid #c9d1db; background: #fff; max-width: 100%; }
"""

_UMSCHALTER = """
var knoepfe = document.querySelectorAll("nav button");
var faelle = document.querySelectorAll(".fall");
function zeige(i) {
  faelle.forEach(function (f, n) { f.hidden = n !== i; });
  knoepfe.forEach(function (k, n) { k.setAttribute("aria-pressed", n === i ? "true" : "false"); });
}
knoepfe.forEach(function (k, n) { k.addEventListener("click", function () { zeige(n); }); });
zeige(0);
"""


def _statische_datei(pfad):
    """Inhalt der statischen Datei zu einer Adresse wie `/static/core/app.css`."""
    vorspann = "/" + settings.STATIC_URL.strip("/") + "/"
    gefunden = finders.find(pfad[len(vorspann) :]) if pfad.startswith(vorspann) else None
    if not gefunden:
        raise ValueError(f"Die Vorschau kann {pfad} nicht einbetten (statische Datei nicht gefunden).")
    return Path(gefunden).read_text(encoding="utf-8").strip()


def _bette_ein(seite, name):
    """Die Seite ohne Verweis auf statische Dateien: Gestaltung und Skript stehen in ihr selbst."""
    skripte = []

    def stil(treffer):
        tag = treffer.group(0)
        pfad = re.search(r"""\bhref=["']([^"']+)["']""", tag)
        if not pfad or "/static/" not in pfad.group(1):
            return tag
        if not re.search(r"""\brel=["']stylesheet["']""", tag, re.IGNORECASE):
            raise ValueError(f"Die Vorschau kann {pfad.group(1)} nicht einbetten (kein Stylesheet), Fall „{name}“.")
        return "<style>\n" + _statische_datei(pfad.group(1)).replace("</style", "<\\/style") + "\n</style>"

    def skript(treffer):
        skripte.append(_statische_datei(treffer.group("pfad")).replace("</", "<\\/"))
        return ""

    seite = _STYLESHEET.sub(stil, seite)
    seite = _SCRIPT.sub(skript, seite)
    uebrig = _RESTLICHE_STATISCHE_DATEI.search(seite)
    if uebrig:
        raise ValueError(f"Die Vorschau kann {uebrig.group(0)} nicht einbetten, Fall „{name}“.")
    ende = "".join(f"<script>\n{text}\n</script>\n" for text in skripte) + _SPERRE
    kopf, trenner, rest = seite.rpartition("</body>")
    return (kopf + ende + trenner + rest) if trenner else (seite + ende)


def _rahmen(seite, titel, breite):
    return (
        f'<div class="ansicht"><h2>{titel}</h2>'
        f'<iframe sandbox="allow-scripts" title="{titel}" width="{breite}" height="{RAHMEN_HOEHE}" '
        f'srcdoc="{html.escape(seite, quote=True)}"></iframe></div>'
    )


def schreibe_vorschau(faelle, ziel, titel="Vorschau"):
    """Schreibt die Vorschau nach `ziel` und gibt den Pfad zurück.

    faelle: Liste von (Name, HTML der fertigen Seite).
    Fehlt der Ordner von `ziel`, wird er angelegt; eine vorhandene Datei wird überschrieben.
    Kann eine Seite nicht vollständig eingebettet werden, wird nichts geschrieben.
    """
    ziel = Path(ziel)
    seiten = [(name, _bette_ein(seite, name)) for name, seite in faelle]
    knoepfe = "".join(f'<button type="button">{html.escape(name)}</button>' for name, _ in seiten)
    bereiche = "".join(
        '<section class="fall">'
        + _rahmen(seite, f"{html.escape(name)}: PC", PC_BREITE)
        + _rahmen(seite, f"{html.escape(name)}: Handy ({HANDY_BREITE} Pixel breit)", HANDY_BREITE)
        + "</section>"
        for name, seite in seiten
    )
    dokument = (
        '<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(titel)}</title><style>{_STIL}</style></head><body>"
        f"<header><h1>{html.escape(titel)}</h1><nav>{knoepfe}</nav>"
        '<p class="hinweis">Nur zum Ansehen: Links und Speichern sind gesperrt, Neuladen und Springen der Seite sind hier nicht zu sehen.</p>'
        f"</header><main>{bereiche}</main><script>{_UMSCHALTER}</script></body></html>\n"
    )
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(dokument, encoding="utf-8")
    return ziel
