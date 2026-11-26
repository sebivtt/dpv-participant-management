"""Einladungstext einer Veranstaltung (#358, VER-05): bereinigen, Zeichen zählen und die ersten Zeilen zeigen.

Bereinigt wird beim Speichern mit nh3 (Abschlusskriterium P3, Frage 6): Übrig bleiben genau die Formatierungen des
Editors, alles andere fällt still weg, der Text selbst bleibt. Danach baut `_Rebuild` das Ergebnis noch einmal aus
dieser kurzen Liste neu auf: Gleichbedeutendes aus anderen Programmen (etwa `<b>` aus Word) wird zur Formatierung
des Editors, Zellen einer Tabelle und weitere Überschriften bleiben als Text getrennt, und Links ohne erlaubte
Adresse werden zu Text (G4). Was dabei herauskommt, ist dasselbe, wenn man es noch einmal bereinigt.
"""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

import nh3
from django.utils.safestring import SafeString, mark_safe

# Die ersten höchstens 300 Zeichen auf Zusammenfassung und Kachel (#358, Frage 10).
EXCERPT_LENGTH = 300
# Erlaubte Links (Frage 3); sie öffnen in neuem Fenster, ohne Herkunftsangabe an die fremde Seite.
URL_SCHEMES = frozenset({"https", "http", "mailto", "tel"})
LINK = 'target="_blank" rel="noopener noreferrer"'

# Was der Editor schreibt (Trix: Absätze als div, die eine Stufe Überschrift als h3, durchgestrichen als del), dazu
# p und s für Text, der ohne Skript von Hand eingegeben ist (E6, Zielbild Ansicht 8). Die Überschrift ist h3, weil der
# Text immer unter einer Überschrift der Ebene 2 steht, etwa „Einladungstext“ in der Kachel.
KEPT = frozenset({"div", "p", "br", "strong", "em", "del", "s", "a", "h3", "blockquote", "ul", "ol", "li"})
# Was nh3 zusätzlich durchlässt, damit `_Rebuild` es umsetzt: gleichbedeutende Formatierungen und Teile, deren Text
# sonst am Nachbarn klebte. Nichts davon bleibt im Ergebnis.
RENAMED = {"b": "strong", "i": "em", "strike": "del", "h1": "h3", "h2": "h3", "h4": "h3", "h5": "h3", "h6": "h3",
           "tr": "div", "section": "div", "article": "div", "header": "div", "footer": "div", "main": "div"}
# Zellen einer Tabelle: nur ihr Text, getrennt durch ein Leerzeichen.
CELLS = frozenset({"td", "th"})
PASSED = KEPT | set(RENAMED) | CELLS | {"table", "thead", "tbody", "tfoot"}
# Ganz weg, mit allem darin (V1): Code, eingebettete Rahmen und Gestaltung.
REMOVED_WITH_CONTENT = frozenset({"script", "style", "iframe", "noscript", "template", "object", "embed", "svg", "math",
                                  "title", "textarea", "select"})
VOID = frozenset({"br"})


def _allowed_link(address: str | None) -> bool:
    if not address:
        return False
    try:
        return urlsplit(address.strip()).scheme.lower() in URL_SCHEMES
    except ValueError:
        return False


class _Rebuild(HTMLParser):
    """Baut das schon von nh3 bereinigte HTML aus der kurzen Liste neu auf; alles mit festem Wortlaut.

    nh3 liefert wohlgeformtes HTML; jedes Ende gehört deshalb zum letzten offenen Element derselben Art.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.open: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        name = RENAMED.get(tag, tag)
        if name in VOID:
            self.out.append("<br>")
            return
        emitted = None
        if name == "a":
            address = dict(attrs).get("href")
            if _allowed_link(address):
                self.out.append(f'<a href="{escape(address.strip())}" {LINK}>')
                emitted = "a"
        elif name in KEPT:
            self.out.append(f"<{name}>")
            emitted = name
        self.open.append((tag, emitted))

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)
        if RENAMED.get(tag, tag) not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if RENAMED.get(tag, tag) in VOID:
            return
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index][0] == tag:
                for _tag, emitted in reversed(self.open[index:]):
                    if emitted:
                        self.out.append(f"</{emitted}>")
                if tag in CELLS:
                    self.out.append(" ")
                del self.open[index:]
                return

    def handle_data(self, data: str) -> None:
        self.out.append(escape(data, quote=False))

    def result(self) -> str:
        self.close()
        for _tag, emitted in reversed(self.open):
            if emitted:
                self.out.append(f"</{emitted}>")
        return "".join(self.out)


def clean(html: str) -> str:
    """Bereinigt einen Einladungstext auf die erlaubten Formatierungen; leer, wenn kein Text übrig ist (G3).

    Erst nh3 (Abschlusskriterium P3), dann der feste Neubau aus `KEPT`. Skripte, Bilder, eingebettete Rahmen,
    Gestaltungsangaben, Klick-Befehle und Links mit anderen Adressen als https, http, mailto und tel fallen weg; der
    übrige Text bleibt (V1, G4, E7). Nur Leerraum oder Formatierung ohne Inhalt ergibt einen leeren Text.
    """
    sanitized = nh3.clean(
        html or "",
        tags=set(PASSED),
        clean_content_tags=set(REMOVED_WITH_CONTENT),
        attributes={"a": {"href"}},
        url_schemes=set(URL_SCHEMES),
        url_relative="deny",
        link_rel=None,
        strip_comments=True,
    )
    builder = _Rebuild()
    builder.feed(sanitized)
    rebuilt = builder.result().strip()
    return rebuilt if _text_of(rebuilt).strip() else ""


class _Tree(HTMLParser):
    """Liest bereinigtes HTML als Baum: je Element (Name, Anfang wie im HTML, Kinder), Text als Zeichenkette."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: list = []
        self.stack: list[list] = [self.root]

    def handle_starttag(self, tag: str, attrs: list) -> None:
        start = self.get_starttag_text()
        node = (tag, start, [])
        self.stack[-1].append(node)
        if tag not in VOID:
            self.stack.append(node[2])

    def handle_endtag(self, tag: str) -> None:
        if tag not in VOID and len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.stack[-1].append(data)


def _tree(html: str) -> list:
    parser = _Tree()
    parser.feed(html)
    parser.close()
    return parser.root


def _visible(data: str) -> str:
    """Der sichtbare Teil eines Texts: ohne Zeilenumbrüche, die im Editor nur die Absätze trennen."""
    return data.replace("\r", "").replace("\n", "")


def _text_of(html: str) -> str:
    found = []

    def walk(nodes: list) -> None:
        for node in nodes:
            if isinstance(node, str):
                found.append(node)
            else:
                walk(node[2])

    walk(_tree(html))
    return _visible("".join(found))


def visible_length(html: str) -> int:
    """Die Zahl der sichtbaren Zeichen, ohne Formatierung und Zeilenumbrüche (Frage 5, #215).

    Gezählt wird je Unicode-Zeichen wie in der Zahl der Zeichen beim Tippen (core/static/core/app.js).
    """
    return len(_text_of(html))


def _serialize(nodes: list) -> str:
    out = []
    for node in nodes:
        if isinstance(node, str):
            out.append(escape(node, quote=False))
        else:
            tag, start, children = node
            out.append(start)
            if tag not in VOID:
                out.append(_serialize(children))
                out.append(f"</{tag}>")
    return "".join(out)


class _Excerpt:
    """Nimmt Text und Elemente der Reihe nach, bis `limit` sichtbare Zeichen erreicht sind (`excerpt()`)."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.left = limit
        # Endete der Platz mitten in einem Text? Dann steht „…“ schon dort.
        self.ended_inline = False

    def text(self, data: str) -> str:
        visible = _visible(data)
        if len(visible) <= self.left:
            self.left -= len(visible)
            return data
        taken = ""
        for word in visible.split(" "):
            candidate = f"{taken} {word}" if taken else word
            if len(candidate) > self.left:
                break
            taken = candidate
        # Ganz vorn ein Wort, länger als der Platz: hart gekürzt, „…“ dann ohne Leerzeichen am Wortrest.
        hard = not taken and self.left == self.limit
        if hard:
            taken = visible[:self.limit]
        self.left = 0
        if not taken.strip():
            return ""
        self.ended_inline = True
        return f"{taken}…" if hard else f"{taken.rstrip()} …"

    def nodes(self, children: list) -> list:
        kept = []
        for node in children:
            if self.left <= 0:
                break
            if isinstance(node, str):
                kept.append(self.text(node))
                continue
            tag, start, inner = node
            if tag in VOID:
                kept.append(node)
                continue
            taken = self.nodes(inner)
            if _text_of(_serialize(taken)).strip():
                kept.append((tag, start, taken))
        return [node for node in kept if node]


def excerpt(html: str, limit: int = EXCERPT_LENGTH) -> SafeString:
    """Die ersten höchstens `limit` sichtbaren Zeichen mit Formatierung, für Zusammenfassung und Kachel (G5).

    Kürzere Texte erscheinen ganz. Ein längerer endet an einer Wortgrenze; jedes offene Element wird geschlossen. Endet
    der Platz mitten in einem Text, steht „…“ dahinter, sonst als eigener Absatz am Ende (Zielbild Ansicht 4). Gibt es
    am Anfang kein Leerzeichen im Platz, wird dort hart gekürzt. Bereinigt wird zuvor noch einmal, damit nur
    Erlaubtes die Seite erreicht, auch wenn etwas Fremdes in der Datenbank stünde.
    """
    nodes = _tree(clean(html))
    whole = _serialize(nodes)
    if visible_length(whole) <= limit:
        return mark_safe(whole)  # noqa: S308 -- aus `clean()`, nur erlaubte Formatierung, Text maskiert
    cutter = _Excerpt(limit)
    shown = _serialize(cutter.nodes(nodes))
    if not cutter.ended_inline:
        shown += "<p>…</p>"
    return mark_safe(shown)  # noqa: S308 -- aus `clean()`, nur erlaubte Formatierung, Text maskiert
