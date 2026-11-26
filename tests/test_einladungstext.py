"""Tests für den Einladungstext mit einfachem Editor, beim Speichern bereinigt (#358, VER-05).

Die Kennungen E1 bis E7, V1 bis V4 und G1 bis G8 verweisen auf die Szenarien vom 17.11.2026 (Fassung nach dem
Zielbild, https://github.com/sebivtt/dpv-participant-management/issues/358#issuecomment-6951036732), die Wortlaute auf
den Text von #358. Was nur ein Browser zeigt (E5 nur mit der Tastatur und am Handy, die Knopfleiste, die Zahl der
Zeichen beim Tippen, das Einfügen in den Editor, Escape im Dialog), prüft `rauchtests/test_einladungstext.py`; hier
steht, was beim Browser ankommt und was danach in der Datenbank steht. „Heute“ ist der 05.01.2028; die Tests stellen
die Uhr des Servers fest. Personen wie in den Szenarien: Wanda (Leitung Pfingstlager 2028), Finn (Mitglied, keine
Leitung), Max (Admin im Support-Zugang), Otto (Konto ohne Zuordnung), Zora (Leitung „Sommerfahrt Zugvögel“). Alle
Namen, Adressen und Nummern sind erfunden; „Burg Ludwigstein“ stammt aus dem Zielbild von #356.
"""

import hashlib
import re
from collections import Counter
from datetime import date, datetime, time
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.utils import timezone

from events import invitation
from events.models import Event
from roles.models import Role
from tests.test_benennen import dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, unit_address
from tests.test_rollen import give, person
from tests.test_veranstaltungen import SCRIPT, build_people, event_address, event_of

R = Role.Kind
pytestmark = pytest.mark.django_db

SAVED = "Der Einladungstext von Pfingstlager 2028 ist gespeichert."
CHANGED = ("Der Einladungstext von Pfingstlager 2028 wurde inzwischen von jemand anderem geändert. Dein Text steht "
           "unten noch im Editor und ist nicht gespeichert. Bitte prüfe ihn und speichere erneut.")
NONE_YET = "Noch kein Einladungstext."
WITHOUT_SCRIPT = "Ohne JavaScript siehst du die Formatierung als Zeichen."
TOO_LONG = "Der Einladungstext ist zu lang: höchstens 10.000 Zeichen, jetzt %s."
# Wie Trix den Text aus E1 speichert: Absätze als div, Überschrift (eine Stufe), Aufzählung und ein Link.
E1_TEXT = ("<div>Liebe Walhallerinnen und Walhaller, liebe Eltern,</div>"
           "<div>zu Pfingsten fahren wir gemeinsam ins <strong>Pfingstlager 2028</strong> auf die Burg. Wir freuen uns "
           "auf vier Tage mit Hajk, Singerunde, Geländespiel und Lagerfeuer – und vor allem auf euch! Bitte lest den "
           "Text ganz durch, bevor ihr euch anmeldet.</div>"
           "<h2>Packliste</h2>"
           "<ul><li>Kluft und Halstuch</li><li>Schlafsack (warm!) und Isomatte</li>"
           "<li>Regenjacke und <em>eingelaufene</em> feste Schuhe</li></ul>"
           '<div>Die <a href="https://example.org/anfahrt">Anfahrt</a> findet ihr hier.</div>')
LINK_ATTRS = 'target="_blank" rel="noopener noreferrer"'


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Heute ist der 05.01.2028, mittags, wie in den Szenarien von #356."""
    moment = timezone.make_aware(datetime(2028, 1, 5, 12, 0))
    monkeypatch.setattr(timezone, "now", lambda: moment)
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 5))


@pytest.fixture
def org():
    o = build_people()
    o.zora = person("zora.zugvogel", "Zora", "Zugvogel")
    give(o.zora, R.MEMBER, o.walhall)
    return o


@pytest.fixture
def pfingstlager(org):
    """Wandas „Pfingstlager 2028“ vom 02.06.2028, 18:00, bis 05.06.2028, 12:00; das Anlegen ist beendet."""
    found = event_of(org.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))
    found.start_time, found.end_time, found.location = time(18, 0), time(12, 0), "Burg Ludwigstein"
    found.save()
    return found


@pytest.fixture
def zugvoegel(org):
    """Zoras „Sommerfahrt Zugvögel“ mit eigenem Einladungstext (V4)."""
    found = event_of(org.zora, "Sommerfahrt Zugvögel", date(2028, 7, 20), date(2028, 7, 30))
    Event.objects.filter(pk=found.pk).update(invitation_text="<div>Treffpunkt am Bahnhof.</div>")
    found.refresh_from_db()
    return found


@pytest.fixture
def entwurf(org):
    """Wandas „Pfingstlager 2028“ nach „Weiter“ in Schritt 1: Das Anlegen läuft noch (#380)."""
    found = event_of(org.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))
    Event.objects.filter(pk=found.pk).update(creating_by=org.wanda)
    found.refresh_from_db()
    return found


# ---------- Adressen und Hilfen ----------


def step_address(entry) -> str:
    """Schritt 2 „Einladungstext“ beim Anlegen."""
    return f"{event_address(entry)}anlegen/einladungstext/"


def basics_address(entry) -> str:
    return f"{event_address(entry)}anlegen/"


def summary_address(entry) -> str:
    return f"{event_address(entry)}anlegen/zusammenfassung/"


def cancel_address(entry) -> str:
    return f"{event_address(entry)}anlegen/abbrechen/"


def dialog_address(entry) -> str:
    """Der Dialog „Einladungstext bearbeiten“ des Stifts der Kachel."""
    return f"{event_address(entry)}einladungstext/"


def stored(entry) -> str:
    entry.refresh_from_db()
    return entry.invitation_text


def set_text(entry, text: str) -> None:
    Event.objects.filter(pk=entry.pk).update(invitation_text=text)
    entry.refresh_from_db()


def editor(root):
    """Der Baustein „Editor“ mit seinem Textfeld, wie er ohne Skript ankommt."""
    return _one(_all(root, lambda e: "a-editor" in _classes(e)))


def editor_text(root) -> str:
    """Der Text im Textfeld des Editors (ohne Skript: die Formatierung als Zeichen)."""
    return _text(_one(_by_tag(editor(root), "textarea", name="invitation_text")))


def version_of(root) -> str:
    return _attr(_one(_by_tag(root, "input", name="invitation_version")), "value")


def progress(root) -> list[tuple[str, bool]]:
    found = _one(_all(root, lambda e: e.name == "ol" and "a-schritte" in _classes(e)))
    return [(_visible_text(step), _attr(step, "aria-current") == "step") for step in _by_tag(found, "li")]


def step_buttons(root) -> dict[str, str]:
    bar = _one(_all(root, lambda e: "a-schritt-knoepfe" in _classes(e)))
    return {_visible_text(element): _attr(element, "href") if element.name == "a" else "senden"
            for element in _all(bar, lambda e: e.name in ("a", "button"))}


def tile(root):
    """Der Abschnitt „Einladungstext“: Kachel der Leitungsseite oder Abschnitt der Zusammenfassung."""
    return _one(_by_tag(root, "section", aria_labelledby="h-einladungstext"))


def pencil(root) -> tuple[str, str]:
    """Wohin der Stift im Abschnitt „Einladungstext“ führt und was Vorleseprogramme hören."""
    found = _one(_all(tile(root), lambda e: "a-stift" in _classes(e)))
    return _attr(found, "href"), _text(_one(_all(found, lambda e: "sr-nur" in _classes(e))))


def tile_html(response) -> str:
    """Das HTML im Abschnitt „Einladungstext“, wie es beim Browser ankommt."""
    page = response.content.decode()
    match = re.search(r'<section[^>]*aria-labelledby="h-einladungstext".*?</section>', page, re.S)
    assert match, "Abschnitt „Einladungstext“ fehlt"
    return match.group(0)


def shown_text(root) -> str:
    """Der Text im Abschnitt, ohne Überschrift und Stift."""
    body = _all(tile(root), lambda e: "a-formatiert" in _classes(e) or "a-leer-satz" in _classes(e))
    return _visible_text(_one(body))


def save_step(client, entry, text: str, version: str | None = None):
    """„Weiter“ in Schritt 2 mit diesem Text."""
    version = version or str(Event.objects.get(pk=entry.pk).invitation_version)
    return client.post(step_address(entry), {"invitation_text": text, "invitation_version": version})


def save_dialog(client, entry, text: str, version: str | None = None):
    """„Speichern“ im Dialog „Einladungstext bearbeiten“."""
    version = version or str(Event.objects.get(pk=entry.pk).invitation_version)
    return client.post(dialog_address(entry), {"invitation_text": text, "invitation_version": version})


def field_error(root) -> str:
    errors = _all(editor(root), lambda e: "invalid-feedback" in _classes(e))
    return _visible_text(_one(errors)) if errors else ""


def open_elements(html: str) -> Counter:
    """Wie oft jedes Element geöffnet, aber nicht geschlossen ist; leer, wenn keine Formatierung offen bleibt."""
    found = Counter()

    class Count(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag != "br":
                found[tag] += 1

        def handle_endtag(self, tag):
            found[tag] -= 1

    Count().feed(html)
    return +found


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-02")
def test_e1_wanda_schreibt_in_schritt_2_und_die_zusammenfassung_zeigt_die_ersten_zeilen(org, entwurf):
    client = client_for(org.wanda)

    root = _tree(client.get(step_address(entwurf)))

    assert progress(root) == [("Schritt 1 Grunddaten", False), ("Schritt 2 Einladungstext", True),
                              ("Schritt 3 Zusammenfassung", False)]
    block = editor(root)
    # Beschriftung nur „Einladungstext“, ohne Zusatz (Nachklärung N1).
    labels = [_visible_text(label) for label in _by_tag(block, "label")]
    assert labels == ["Einladungstext"]
    # Die Zahl der Zeichen schreibt das Skript beim Tippen (#215); der Server bringt die Stelle mit der Grenze mit.
    counter = _one(_all(block, lambda e: "a-zeichenzahl" in _classes(e)))
    assert _attr(counter, "data-vorlesen") == "{anzahl} von 10.000 Zeichen"
    assert _attr(_one(_by_tag(block, "textarea")), "data-hoechstens") == "10000"
    assert step_buttons(root) == {"Abbrechen": cancel_address(entwurf), "Zurück": basics_address(entwurf),
                                  "Weiter": "senden"}

    response = save_step(client, entwurf, E1_TEXT)

    assert response.status_code == 302
    assert response.url == summary_address(entwurf)
    assert "<h2>Packliste</h2>" in stored(entwurf)
    assert f'<a href="https://example.org/anfahrt" {LINK_ATTRS}>Anfahrt</a>' in stored(entwurf)
    page = client.get(response.url)
    root = _tree(page)
    assert progress(root)[2] == ("Schritt 3 Zusammenfassung", True)
    assert pencil(root) == (step_address(entwurf), "Einladungstext ändern")
    html = tile_html(page)
    assert "<strong>Pfingstlager 2028</strong>" in html
    assert shown_text(root).endswith("…")
    assert "Isomatte" not in shown_text(root)


@pytest.mark.rechtematrix("VA-02")
def test_e2_leer_weiter_und_zusammenfassung_und_kachel_sagen_noch_kein_einladungstext(org, entwurf):
    client = client_for(org.wanda)

    response = save_step(client, entwurf, "")

    assert response.url == summary_address(entwurf)
    assert stored(entwurf) == ""
    assert shown_text(_tree(client.get(summary_address(entwurf)))) == NONE_YET
    client.post(summary_address(entwurf))
    assert shown_text(_tree(client.get(event_address(entwurf)))) == NONE_YET


@pytest.mark.rechtematrix("VA-02")
def test_e3_stift_der_kachel_oeffnet_den_breiten_dialog_mit_dem_ganzen_text(org, pfingstlager):
    set_text(pfingstlager, invitation.clean(E1_TEXT))
    client = client_for(org.wanda)
    assert pencil(_tree(client.get(event_address(pfingstlager)))) == (dialog_address(pfingstlager),
                                                                      "Einladungstext bearbeiten")

    root = _tree(client.get(dialog_address(pfingstlager)))

    dialog = dialog_of(root)
    assert "ist-breit" in _classes(dialog)
    assert _text(_one(_by_tag(dialog, "h2"))) == "Einladungstext bearbeiten"
    assert _visible_text(_one(_all(dialog, lambda e: "a-unterzeile" in _classes(e)))) == "Pfingstlager 2028"
    # Der ganze Text, nicht nur die ersten 300 Zeichen.
    assert "Isomatte" in editor_text(dialog)
    footer = _one(_all(dialog, lambda e: "a-dialog-fuss" in _classes(e)))
    assert _attr(_one(_by_tag(footer, "a")), "href") == event_address(pfingstlager)
    form = _one(_by_tag(footer, "form"))
    assert _attr(form, "action") == dialog_address(pfingstlager)
    assert "btn-primary" in _classes(_one(_by_tag(form, "button")))
    assert _attr(_one(_by_tag(dialog, "textarea")), "form") == _attr(form, "id")

    longer = "<div><ol><li>Anmeldung im Tool bis 30.04.2028</li></ol></div>" + editor_text(dialog)
    response = save_dialog(client, pfingstlager, longer, version_of(root))

    assert response.status_code == 302
    assert response.url == event_address(pfingstlager)
    page = client.get(response.url)
    assert short_notices(page) == [SAVED]
    assert "<ol><li>Anmeldung im Tool bis 30.04.2028</li></ol>" in tile_html(page)
    assert "Anmeldung im Tool" in stored(pfingstlager)


@pytest.mark.rechtematrix("VA-02")
def test_e4_alle_erlaubten_formatierungen_bleiben_und_links_oeffnen_in_neuem_fenster(org, pfingstlager):
    text = ("<div><strong>fett</strong> <em>kursiv</em> <del>durch</del></div><h2>Packliste</h2>"
            "<blockquote>Zitat</blockquote><ul><li>Punkt</li></ul><ol><li>Nummer</li></ol>"
            '<div><a href="https://example.org/a">sicher</a> <a href="http://example.org/b">alt</a> '
            '<a href="mailto:wanda@example.org">Mail</a> <a href="tel:+490000000000">Telefon</a></div>')

    save_dialog(client_for(org.wanda), pfingstlager, text)

    saved = stored(pfingstlager)
    for part in ("<strong>fett</strong>", "<em>kursiv</em>", "<del>durch</del>", "<h2>Packliste</h2>",
                 "<blockquote>Zitat</blockquote>", "<ul><li>Punkt</li></ul>", "<ol><li>Nummer</li></ol>",
                 f'<a href="https://example.org/a" {LINK_ATTRS}>sicher</a>',
                 f'<a href="http://example.org/b" {LINK_ATTRS}>alt</a>',
                 f'<a href="mailto:wanda@example.org" {LINK_ATTRS}>Mail</a>',
                 f'<a href="tel:+490000000000" {LINK_ATTRS}>Telefon</a>'):
        assert part in saved, part
    html = tile_html(client_for(org.wanda).get(event_address(pfingstlager)))
    assert f'<a href="https://example.org/a" {LINK_ATTRS}>sicher</a>' in html


@pytest.mark.rechtematrix("VA-02")
def test_e6_ohne_skript_textfeld_mit_formatierung_als_zeichen(org, pfingstlager):
    set_text(pfingstlager, "<div>Die Anfahrt steht unten.</div>")
    client = client_for(org.wanda)

    root = _tree(client.get(dialog_address(pfingstlager)))

    block = editor(root)
    assert editor_text(root) == "<div>Die Anfahrt steht unten.</div>"
    assert WITHOUT_SCRIPT in _visible_text(block)
    # Der Satz steht mit dem Feld verknüpft, damit Vorleseprogramme ihn beim Betreten vorlesen.
    sentence = _one(_all(block, lambda e: "a-editor-ohne-skript" in _classes(e)))
    assert _attr(sentence, "id") in (_attr(_one(_by_tag(block, "textarea")), "aria-describedby") or "").split()

    save_dialog(client, pfingstlager, "<div>Die <strong>Anfahrt</strong> steht unten.</div>", version_of(root))

    assert "<strong>Anfahrt</strong>" in tile_html(client.get(event_address(pfingstlager)))


@pytest.mark.rechtematrix("VA-02")
def test_e7_eingefuegtes_aus_word_behaelt_nur_die_erlaubten_formatierungen(org, pfingstlager):
    word = ('<p class="MsoNormal" style="margin:0;font-family:Calibri"><span style="color:#C00000;font-size:14pt">'
            '<b>Packliste</b></span><o:p></o:p></p>'
            '<table class="MsoTableGrid" border="1"><tr><td style="width:200px">Kluft</td><td>Halstuch</td></tr>'
            '<tr><td>Schlafsack</td><td><font face="Comic Sans MS" color="red">Isomatte</font></td></tr></table>'
            '<p class="MsoListParagraph"><i>Regenjacke</i></p>')

    save_dialog(client_for(org.wanda), pfingstlager, word)

    saved = stored(pfingstlager)
    for word_part in ("Packliste", "Kluft", "Halstuch", "Schlafsack", "Isomatte", "Regenjacke"):
        assert word_part in saved
    # Kein Wort klebt am nächsten, auch nicht aus den Zellen der Tabelle.
    assert "KluftHalstuch" not in saved and "SchlafsackIsomatte" not in saved
    for gone in ("style", "class", "<span", "<table", "<td", "<font", "<o:p", "border"):
        assert gone not in saved, gone
    assert "<strong>Packliste</strong>" in saved
    assert "<em>Regenjacke</em>" in saved


# ---------- Verboten ----------


V1_TEXT = ('<div>Willkommen</div><script>document.title = "gekapert"</script>'
           '<img src="x" onerror="alert(1)"><div><a href="javascript:alert(2)">Klick</a></div>'
           '<iframe src="https://example.org/rahmen"></iframe><div style="position:fixed;color:red">Rot</div>'
           '<div onclick="alert(3)">Text</div><svg onload="alert(4)"></svg>')


@pytest.mark.rechtematrix("VA-02")
def test_v1_eingeschleuster_code_wird_beim_speichern_entfernt_und_laeuft_nirgends(org, entwurf):
    client = client_for(org.wanda)

    save_step(client, entwurf, V1_TEXT)

    saved = stored(entwurf)
    for gone in ("script", "gekapert", "<img", "onerror", "alert", "javascript", "iframe", "style", "onclick",
                 "svg", "onload"):
        assert gone not in saved, gone
    for kept in ("Willkommen", "Klick", "Rot", "Text"):
        assert kept in saved, kept
    client.post(summary_address(entwurf))
    for address in (event_address(entwurf), dialog_address(entwurf)):
        html = client.get(address).content.decode()
        for gone in ("<script>document", "onerror=", "javascript:alert", "<iframe", "position:fixed", "onclick="):
            assert gone not in html, (address, gone)


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/einladungstext/")
def test_v2_finn_bekommt_beim_dialog_und_beim_speichern_nicht_gefunden(org, pfingstlager):
    set_text(pfingstlager, "<div>Bleibt so.</div>")
    client = client_for(org.finn)

    assert_like_missing(org.finn, dialog_address(pfingstlager))
    assert client.get(dialog_address(pfingstlager), **SCRIPT).status_code == 404
    assert save_dialog(client, pfingstlager, "<div>Gekapert</div>").status_code == 404

    assert stored(pfingstlager) == "<div>Bleibt so.</div>"


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/einladungstext/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/einladungstext/")
def test_v3_max_im_support_zugang_und_otto_ebenso_nicht_gefunden(org, pfingstlager, entwurf):
    set_text(pfingstlager, "<div>Bleibt so.</div>")
    max_client = client_for(org.max)
    assert max_client.post(f"{unit_address(org.walhall)}support-zugang/", {"anlass": "lead_request"}).status_code == 302

    for user, client in ((org.max, max_client), (org.otto, client_for(org.otto))):
        for address in (dialog_address(pfingstlager), step_address(entwurf)):
            assert client.get(address).status_code == 404, (user.username, address)
            assert client.post(address, {"invitation_text": "<div>Gekapert</div>",
                                         "invitation_version": "1"}).status_code == 404, (user.username, address)
    assert_like_missing(org.otto, dialog_address(pfingstlager))
    assert_like_missing(org.otto, step_address(entwurf))
    # Auch eine andere Leitung legt den Entwurf nicht an und kommt nicht in Schritt 2 (VA-06, #380 BV1).
    entwurf.leads.add(org.zora)
    assert_like_missing(org.zora, step_address(entwurf))

    assert stored(pfingstlager) == "<div>Bleibt so.</div>"
    assert stored(entwurf) == ""


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/einladungstext/")
def test_v4_wanda_tauscht_die_kennung_gegen_die_der_sommerfahrt_zugvoegel(org, pfingstlager, zugvoegel):
    client = client_for(org.wanda)
    form = {"invitation_text": "<div>Gekapert</div>", "invitation_version": "1"}

    assert client.post(dialog_address(zugvoegel), form).status_code == 404
    assert client.get(dialog_address(zugvoegel)).status_code == 404
    assert_like_missing(org.wanda, dialog_address(zugvoegel))

    assert stored(zugvoegel) == "<div>Treffpunkt am Bahnhof.</div>"
    # Gegenprobe: Zora darf ihren eigenen Text weiter bearbeiten.
    assert client_for(org.zora).get(dialog_address(zugvoegel)).status_code == 200


# ---------- Grenzfälle ----------


@pytest.mark.rechtematrix("VA-02")
def test_g1_mehr_als_10000_zeichen_meldung_am_feld_und_der_text_bleibt(org, pfingstlager):
    client = client_for(org.wanda)
    too_long = "<div>" + "a" * 10_001 + "</div>"

    response = save_dialog(client, pfingstlager, too_long)

    assert response.status_code == 200
    root = _tree(response)
    assert field_error(root) == TOO_LONG % "10.001"
    assert editor_text(root) == too_long
    textarea = _one(_by_tag(editor(root), "textarea"))
    assert "is-invalid" in _classes(textarea) and _attr(textarea, "aria-invalid") == "true"
    assert stored(pfingstlager) == ""

    # Genau 10.000 gehen, auch in Schritt 2; Formatierung zählt nicht mit.
    exactly = "<div><strong>" + "a" * 5_000 + "</strong></div><h2>" + "b" * 5_000 + "</h2>"
    assert save_dialog(client, pfingstlager, exactly).status_code == 302
    assert invitation.visible_length(stored(pfingstlager)) == 10_000


@pytest.mark.rechtematrix("VA-02")
def test_g1_auch_in_schritt_2_bleibt_der_zu_lange_text_und_nichts_wird_gespeichert(org, entwurf):
    response = save_step(client_for(org.wanda), entwurf, "<div>" + "ä" * 10_001 + "</div>")

    assert response.status_code == 200
    assert field_error(_tree(response)) == TOO_LONG % "10.001"
    assert stored(entwurf) == ""


@pytest.mark.rechtematrix("VA-02")
def test_g2_aelteres_fenster_ueberschreibt_nichts_und_der_eigene_text_bleibt(org, pfingstlager):
    set_text(pfingstlager, "<div>Stand vorher</div>")
    first, second = client_for(org.wanda), client_for(org.wanda)
    old = version_of(_tree(first.get(dialog_address(pfingstlager))))
    assert version_of(_tree(second.get(dialog_address(pfingstlager)))) == old

    assert save_dialog(first, pfingstlager, "<div>Aus dem ersten Fenster</div>", old).status_code == 302
    response = save_dialog(second, pfingstlager, "<div>Aus dem zweiten Fenster</div>", old)

    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    warning = _one(_all(dialog, lambda e: "a-meldung" in _classes(e)))
    assert "ist-warnung" in _classes(warning)
    assert CHANGED in _visible_text(warning)
    assert editor_text(dialog) == "<div>Aus dem zweiten Fenster</div>"
    assert stored(pfingstlager) == "<div>Aus dem ersten Fenster</div>"

    # Danach speichert sie bewusst erneut: Das geht, ohne Sperre.
    assert save_dialog(second, pfingstlager, "<div>Aus dem zweiten Fenster</div>",
                       version_of(dialog)).status_code == 302
    assert stored(pfingstlager) == "<div>Aus dem zweiten Fenster</div>"


@pytest.mark.rechtematrix("VA-02")
def test_g2_grunddaten_aus_einem_zweiten_fenster_aendern_den_einladungstext_nicht(org, pfingstlager):
    client = client_for(org.wanda)
    old = version_of(_tree(client.get(dialog_address(pfingstlager))))
    Event.objects.filter(pk=pfingstlager.pk).update(location="Zeltplatz Moor", version=5)

    assert save_dialog(client, pfingstlager, "<div>Neu</div>", old).status_code == 302
    assert stored(pfingstlager) == "<div>Neu</div>"


@pytest.mark.rechtematrix("VA-02")
@pytest.mark.parametrize("empty", ["   ", "<div><br></div><div><br></div>", "<div>&nbsp; &nbsp;</div>",
                                   "<strong> </strong><em></em><ul><li></li></ul>", "\n\n<h2> </h2>\n"])
def test_g3_nur_leerraum_oder_formatierung_ohne_inhalt_gilt_als_leer(org, pfingstlager, empty):
    client = client_for(org.wanda)

    assert save_dialog(client, pfingstlager, empty).status_code == 302

    assert stored(pfingstlager) == ""
    assert shown_text(_tree(client.get(event_address(pfingstlager)))) == NONE_YET


@pytest.mark.rechtematrix("VA-02")
@pytest.mark.parametrize("address", ["ftp://example.org/plan.pdf", "data:text/html,Hallo", "/relativ", "#oben",
                                     "JaVaScRiPt:alert(1)", "vbscript:x"])
def test_g4_andere_links_werden_entfernt_das_wort_bleibt_als_text(org, pfingstlager, address):
    save_dialog(client_for(org.wanda), pfingstlager, f'<div>Der <a href="{address}">Lageplan</a> folgt.</div>')

    assert stored(pfingstlager) == "<div>Der Lageplan folgt.</div>"


@pytest.mark.rechtematrix("VA-02")
def test_g5_kurzer_text_erscheint_ganz_ein_langer_gekuerzt_ohne_offene_formatierung(org, pfingstlager):
    client = client_for(org.wanda)
    short = "<div>Kurz und <strong>knapp</strong>.</div>"
    set_text(pfingstlager, short)
    assert shown_text(_tree(client.get(event_address(pfingstlager)))) == "Kurz und knapp ."
    assert "…" not in tile_html(client.get(event_address(pfingstlager)))

    long = "<div>" + "Wort " * 50 + "<strong>" + "fett " * 40 + "</strong>und noch mehr Text danach.</div>"
    set_text(pfingstlager, invitation.clean(long))

    root = _tree(client.get(event_address(pfingstlager)))
    text = shown_text(root)
    assert text.endswith("…")
    without = text.removesuffix("…").strip()
    assert len(without.replace(" ", "")) <= 300 and len(without) <= 300
    # An einer Wortgrenze gekürzt: Am Ende steht ein ganzes Wort.
    assert without.split()[-1] in ("Wort", "fett")
    # Ohne offene Formatierung: Jedes geöffnete Element ist auch geschlossen.
    shown = str(invitation.excerpt(stored(pfingstlager)))
    assert "<strong>" in shown
    assert open_elements(shown) == Counter()
    assert open_elements(tile_html(client.get(event_address(pfingstlager)))) == Counter()


def test_g5_kuerzen_genau_an_300_zeichen_und_bei_einem_ganz_langen_wort():
    exactly = "<div>" + "a" * 300 + "</div>"
    assert invitation.excerpt(exactly) == exactly
    assert "…" in invitation.excerpt("<div>" + "a" * 301 + "</div>")
    assert invitation.visible_length(str(invitation.excerpt("<div>" + "a" * 400 + "</div>")).replace("…", "")) <= 300
    # Endet der Platz genau an einem Absatz, steht „…“ als eigener Absatz dahinter (Zielbild Ansicht 4).
    blocks = "<div>" + "a" * 300 + "</div><div>Weiter</div>"
    assert invitation.excerpt(blocks) == "<div>" + "a" * 300 + "</div><p>…</p>"


@pytest.mark.rechtematrix("VA-02")
def test_g6_veranstaltungen_aus_p2_haben_noch_keinen_einladungstext(org):
    probe = event_of(org.wanda, "Probelager 2028", date(2028, 5, 15), date(2028, 5, 17))

    assert probe.invitation_text == ""
    assert shown_text(_tree(client_for(org.wanda).get(event_address(probe)))) == NONE_YET


@pytest.mark.rechtematrix("VA-02")
def test_g7_abbrechen_aendert_nichts_und_zurueck_und_weiter_behaelt_den_text(org, entwurf):
    client = client_for(org.wanda)
    save_step(client, entwurf, "<div>Gespeichert</div>")
    client.post(summary_address(entwurf))
    root = _tree(client.get(dialog_address(entwurf)))
    dialog = dialog_of(root)
    assert _attr(_one(_all(dialog, lambda e: "a-schliessen" in _classes(e))), "href") == event_address(entwurf)
    assert _attr(dialog, "data-schliessen") == event_address(entwurf)
    assert stored(entwurf) == "<div>Gespeichert</div>"


@pytest.mark.rechtematrix("VA-02")
def test_g7_zurueck_aus_schritt_2_und_wieder_weiter_der_gespeicherte_text_ist_noch_da(org, entwurf):
    client = client_for(org.wanda)
    save_step(client, entwurf, "<div>Gespeichert</div>")

    assert step_buttons(_tree(client.get(step_address(entwurf))))["Zurück"] == basics_address(entwurf)
    assert step_buttons(_tree(client.get(summary_address(entwurf))))["Zurück"] == step_address(entwurf)
    root = _tree(client.get(step_address(entwurf)))

    assert editor_text(root) == "<div>Gespeichert</div>"
    assert save_step(client, entwurf, editor_text(root), version_of(root)).url == summary_address(entwurf)
    assert stored(entwurf) == "<div>Gespeichert</div>"


@pytest.mark.rechtematrix("VA-02")
def test_g8_waehrend_das_lager_laeuft_aendert_wanda_den_text(org, pfingstlager, monkeypatch):
    Event.objects.filter(pk=pfingstlager.pk).update(published=True)
    during = timezone.make_aware(datetime(2028, 6, 3, 10, 0))
    monkeypatch.setattr(timezone, "now", lambda: during)
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 6, 3))
    client = client_for(org.wanda)

    response = save_dialog(client, pfingstlager, "<div>Heute Abend Singerunde.</div>")

    assert response.status_code == 302
    assert stored(pfingstlager) == "<div>Heute Abend Singerunde.</div>"
    assert short_notices(client.get(response.url)) == [SAVED]


# ---------- Sicherheitsrichtlinie (#278, Frage 1) ----------


def _style_sources(response) -> list[str]:
    policy = response["Content-Security-Policy"]
    part = next(entry for entry in policy.split(";") if entry.strip().startswith("style-src"))
    return part.split()[1:]


@pytest.mark.rechtematrix("VA-02")
def test_seiten_mit_editor_erlauben_nur_die_gestaltung_von_trix_mit_schluessel_je_aufruf(org, entwurf, pfingstlager):
    client = client_for(org.wanda)
    nonces = []
    for address in (step_address(entwurf), dialog_address(pfingstlager)):
        response = client.get(address)
        sources = _style_sources(response)
        assert sources[0] == "'self'" and len(sources) == 2, sources
        nonce = re.fullmatch(r"'nonce-([^']+)'", sources[1]).group(1)
        root = _tree(response)
        meta = _one(_by_tag(root, "meta", name="trix-csp-nonce"))
        assert _attr(meta, "content") == nonce
        assert "/static/core/trix/trix.umd.min.js" in response.content.decode()
        nonces.append(nonce)
        # Nur die Gestaltung bekommt die Ausnahme; Skripte bleiben nur vom eigenen Server.
        policy = response["Content-Security-Policy"]
        assert "script-src 'self';" in policy + ";" and "unsafe" not in policy
    assert nonces[0] != nonces[1]
    assert _style_sources(client.get(dialog_address(pfingstlager))) != _style_sources(client.get(dialog_address(pfingstlager)))


@pytest.mark.rechtematrix("VA-02")
def test_seiten_ohne_editor_bleiben_unveraendert_streng(org, entwurf, pfingstlager):
    client = client_for(org.wanda)
    save_step(client, entwurf, "<div>Text</div>")
    for address in (event_address(pfingstlager), summary_address(entwurf), "/veranstaltungen/", "/profil/",
                    f"{event_address(pfingstlager)}bearbeiten/"):
        response = client.get(address)
        assert _style_sources(response) == ["'self'"], address
        content = response.content.decode()
        assert "trix-csp-nonce" not in content and "trix.umd.min.js" not in content, address


# ---------- Bereinigen (Frage 6) ----------


def test_bereinigen_ist_beim_zweiten_mal_ohne_aenderung():
    once = invitation.clean(V1_TEXT + E1_TEXT)

    assert invitation.clean(once) == once


def test_sichtbare_zeichen_ohne_formatierung_und_zeilenumbrueche():
    assert invitation.visible_length("<div><strong>ab</strong> c</div><ul><li>d</li></ul>") == 5
    assert invitation.visible_length("<div>ä&nbsp;ö</div>") == 3
    assert invitation.visible_length("<div>a<br>b</div>\n<div>c</div>") == 3
    # Ein Emoji zählt eins, wie in der Zahl der Zeichen beim Tippen (#215).
    assert invitation.visible_length("<div>🏕️</div>") == len("🏕️")


# ---------- Bausteinkatalog (#176) ----------


@pytest.mark.bausteinkatalog
def test_katalog_zeigt_den_editor_und_die_breite_form_des_dialogs(settings, org):
    settings.BUILDING_BLOCKS_VISIBLE = True
    response = client_for(org.wanda).get("/bausteine/")
    root = _tree(response)

    entry = _one(_by_tag(root, "section", aria_labelledby="h-editor"))
    assert _text(_one(_by_tag(entry, "h2"))) == "Editor"
    assert "#358" in _visible_text(entry)
    assert _one(_all(entry, lambda e: "a-editor" in _classes(e)))
    dialog = _one(_by_tag(root, "section", aria_labelledby="h-dialog"))
    assert _all(dialog, lambda e: e.name == "dialog" and "ist-breit" in _classes(e))
    # Auch im Katalog bekommt nur die Gestaltung von Trix die Ausnahme (Frage 1).
    assert _attr(_one(_by_tag(root, "meta", name="trix-csp-nonce")), "content") in response["Content-Security-Policy"]


# ---------- Zielbild ----------

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "einladungstext.html"
CHECKSUM = "ca32a675f7265f55d64aa2fe4e6746a669a1824caa63f66b168ed7ae2412d468"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Einladungstext", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "17.11.2026", "Orientierung, keine Anforderung", "Abweichungen", "#358"):
        assert must in section[1].split("\n## ", 1)[0], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)


# ---------- Trix vom eigenen Server (CONTRIBUTING.md, Abschnitt 6) ----------


def test_trix_liegt_mit_fassung_und_lizenz_auf_dem_eigenen_server():
    folder = ROOT / "core" / "static" / "core" / "trix"
    script = (folder / "trix.umd.min.js").read_text()

    assert script.startswith("/*\nTrix 2.1.19\n")
    assert "Permission is hereby granted, free of charge" in (folder / "LICENSE").read_text()
    # Prüfsumme der Datei aus dem Paket trix 2.1.19 von npm, unverändert.
    assert hashlib.sha256((folder / "trix.umd.min.js").read_bytes()).hexdigest() == TRIX_CHECKSUM


TRIX_CHECKSUM = "5dcaa7c434ae9f3cf1a53651ea74bfad10cd6423c72cb86a8694969aaff67e51"
