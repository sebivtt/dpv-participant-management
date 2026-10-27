"""Alle Texte der Oberfläche laufen über gettext, nichts steht fest in den Vorlagen (NFA-02, #7).

Geprüft werden die Vorlagen des Tools: Was nach dem Entfernen von übersetzten Texten,
Platzhaltern, Kommentaren, Skripten, Gestaltung und Symbolen noch an Wörtern übrig ist,
steht fest im HTML und ließe sich nicht übersetzen. Das gilt auch für Beschriftungen, die
nur Bildschirmleser vorlesen (aria-label) oder die beim Darauf-Zeigen erscheinen (title).
Texte in Python-Dateien prüft die Durchsicht (CONTRIBUTING.md, Abschnitt 1).
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = sorted(p for app in ("accounts", "core") for p in (BASE_DIR / app / "templates").rglob("*.html"))

# Attribute, deren Inhalt Menschen lesen oder hören.
READ_ATTRIBUTES = {"aria-label", "title", "placeholder", "alt"}
LETTERS = re.compile(r"[A-Za-zÄÖÜäöüß]")

REMOVE = [
    re.compile(r"{#.*?#}", re.S),
    re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.S),
    re.compile(r"{%\s*blocktranslate\b.*?{%\s*endblocktranslate\s*%}", re.S),
    re.compile(r"{%.*?%}", re.S),
    re.compile(r"{{.*?}}", re.S),
    re.compile(r"<(script|style|svg)\b.*?</\1>", re.S),
    re.compile(r"<!doctype[^>]*>", re.I),
]


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in READ_ATTRIBUTES and value and LETTERS.search(value):
                self.found.append(f'{name}="{value}"')

    def handle_data(self, data):
        if LETTERS.search(data):
            self.found.append(data.strip())


def hardcoded_texts(source: str) -> list[str]:
    """Gibt die Texte einer Vorlage zurück, die nicht über gettext laufen."""
    for pattern in REMOVE:
        source = pattern.sub(" ", source)
    collector = _Collector()
    collector.feed(source)
    return collector.found


def test_pruefung_bemerkt_feste_texte_und_laesst_uebersetzte_durch():
    assert hardcoded_texts("<p>Abmelden</p>") == ["Abmelden"]
    assert hardcoded_texts('<a aria-label="Mein Profil" href="/">{{ x }}</a>') == ['aria-label="Mein Profil"']
    assert hardcoded_texts('<p>{% translate "Abmelden" %}</p><a aria-label="{% translate "Mein Profil" %}"></a>') == []
    assert hardcoded_texts("{% blocktranslate %}Hallo {{ name }}!{% endblocktranslate %}") == []


def test_es_gibt_vorlagen_zu_pruefen():
    names = {p.name for p in TEMPLATES}
    assert {"login.html", "start.html", "500.html", "bausteine.html"} <= names


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: str(p.relative_to(BASE_DIR)))
def test_keine_festen_texte_in_den_vorlagen(template):
    assert hardcoded_texts(template.read_text()) == []
