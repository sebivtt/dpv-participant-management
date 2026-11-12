"""Bausteine der Grundgestaltung für die Vorlagen (#7): Symbole, Meldungen (#165), kurze Meldungen (#186), Textfelder (#111), Felder zum Antippen (#180), Fußbereich, Band der Testumgebung (#58).

Alle Bausteine kommen ohne Anfrage, Sitzung und Datenbank aus, damit sie auch auf der
Fehlerseite funktionieren (core/errors.py).
"""

from django import template
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy

register = template.Library()

@register.simple_tag
def icon(name: str) -> SafeString:
    """Ein Symbol aus core/templates/core/_symbole.svg; für Bildschirmleser ausgeblendet.

    Symbole ergänzen Beschriftungen, sie ersetzen sie nie. Wo ein Symbol allein steht,
    bekommt sein Knopf oder Link selbst eine Beschriftung.
    """
    return format_html('<svg class="ic" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>', name)


# Je Art einer Meldung: Klasse, Symbol und das Wort, das Vorleseprogramme vorweg ansagen. Die
# Schlüssel sind die Stufen von Djangos Meldungen (message.level_tag), damit die Login-Seite sie
# direkt weitergeben kann. Farben wie die Statuskennzeichen (core/static/core/app.css).
MESSAGE_KINDS = {
    "info": ("ist-info", "info", gettext_lazy("Information:")),
    "warning": ("ist-warnung", "hinweis", gettext_lazy("Warnung:")),
    "error": ("ist-fehler", "nein", gettext_lazy("Fehler:")),
    "success": ("ist-erfolg", "erfolg", gettext_lazy("Erfolg:")),
}

# Nach einer Handlung angesagt: Warnung und Fehler sofort, Info und Erfolg, sobald das
# Vorleseprogramm frei ist.
LIVE_ROLES = {"info": "status", "success": "status", "warning": "alert", "error": "alert"}


@register.inclusion_tag("core/_meldung.html")
def meldung(kind: str, text: str = "", title: str = "", icon: str = "", live: bool = False, element_id: str = "") -> dict:
    """Meldung einer der vier Arten (#165, docs/gestaltung.md): Info, Warnung, Fehler, Erfolg.

    `title` steht fett als eigene Zeile über `text`. Ein passenderes Symbol als das der Art
    ist erlaubt (`icon`, z. B. das Schloss). Die Art ist nie nur Farbe: Jede hat ihr Symbol,
    und Vorleseprogramme hören vorweg ihr Wort, etwa „Warnung:“. `live` nur für Meldungen
    nach einer Handlung (Login-Seite); fest auf einer Seite stehende werden nicht ungefragt
    angesagt. Eine unbekannte Art, etwa eine eigene Stufe einer Django-Meldung, erscheint als
    Information, statt die Seite mit einem Serverfehler zu sperren. `element_id` gibt der Meldung
    eine Kennung, etwa um sie mit einem Feld zu verknüpfen.
    """
    kind = kind if kind in MESSAGE_KINDS else "info"
    css_class, icon_name, prefix = MESSAGE_KINDS[kind]
    return {
        "css_class": css_class,
        "icon_name": icon or icon_name,
        "prefix": prefix,
        "role": LIVE_ROLES[kind] if live else "note",
        "title": title,
        "text": text,
        "element_id": element_id,
    }


# Nur diese Arten werden kurz (#186, Frage 1): Sie bestätigen eine eigene Handlung, und es ist
# nichts zu tun. Bei Fehler und Warnung muss man etwas tun; verschwänden sie, übersähe man sie.
SHORT_KINDS = ("info", "success")


@register.inclusion_tag("core/_kurzmeldung.html")
def kurzmeldung(kind: str, text: str) -> dict:
    """Kurze Meldung nach einer eigenen Handlung (#186, docs/gestaltung.md), etwa „Dein Fahrtenname ist gespeichert.“

    Aufbau, Farbe und Symbol wie die Meldung derselben Art (`meldung`), dazu ein ×. Das Skript
    (core/static/core/app.js) blendet sie unten über dem Inhalt ein, wo Vorleseprogramme sie
    ansagen, und nach rund 6 Sekunden wieder aus. Ohne Skript steht sie fest an ihrem Platz,
    angesagt wie jede Meldung nach einer Handlung. Fehler und Warnungen werden nie kurz: Sie
    erscheinen hier als feste Meldung.
    """
    context = meldung(kind, text=text, live=True)
    context["short"] = kind in SHORT_KINDS
    return context


def _textfeld(field, described_by: str = "") -> dict:
    """Feld und Fehler für beide Bausteine; dazu die Stelle für die Zahl der Zeichen (#215).

    Die Zahl gibt es nur bei einer fachlichen Grenze, die das Formular am Feld festlegt
    (`data-hoechstens`, dazu die Meldung „zu lang“ als `data-zu-lang`). Der Server liefert die
    Stelle leer und versteckt; das Skript (core/static/core/app.js) schreibt die Zahl beim
    Tippen. Sie ist mit der Eingabe verknüpft, damit Vorleseprogramme sie beim Betreten vorlesen.
    """
    error_id = f"{field.auto_id}-fehler"
    limit = field.field.widget.attrs.get("data-hoechstens")
    counter_id = f"{field.auto_id}-zahl" if limit else ""
    attrs = {"class": "form-control"}
    if field.errors:
        attrs = {"class": "form-control is-invalid", "aria-invalid": "true"}
        described_by = error_id
    described_by = " ".join(filter(None, [described_by, counter_id]))
    if described_by:
        attrs["aria-describedby"] = described_by
    # Sichtbar „12/30“; Vorleseprogramme hören „12 von 30 Zeichen“ statt eines Bruchs oder Datums.
    counter = format_html(
        '<p class="a-zeichenzahl" id="{}" data-vorlesen="{}" hidden><span aria-hidden="true"></span>'
        '<span class="sr-nur"></span></p>',
        counter_id,
        gettext_lazy("{anzahl} von %(hoechstens)s Zeichen") % {"hoechstens": limit},
    ) if limit else ""
    return {
        "field": field,
        "widget": field.as_widget(attrs=attrs),
        "errors": field.errors,
        "error_id": error_id,
        "counter": counter,
        "required": field.field.required,
    }


@register.inclusion_tag("core/_textfeld.html")
def textfeld(field, button: str = "", help_text: str = "") -> dict:
    """Gemeinsamer Baustein für Textfelder (#111), den jedes Formular statt eines eigenen Felds einbindet.

    `field` ist ein Feld eines Django-Formulars. Die Beschriftung steht über dem Feld, bei
    Pflichtfeldern mit „(Pflicht)“. Ein Fehler steht rot direkt darunter, ist mit dem Feld
    verknüpft und keine Meldung der vier Arten (docs/gestaltung.md). Die passende Tastatur am
    Handy (z. B. `autocapitalize`, `autocorrect`, `inputmode`) legt das Formular am Feld fest,
    weil nur es weiß, ob ein Name, ein Satz oder eine Mail hineingehört.

    Als Suchfeld (#190) steht mit `button` ein Knopf zum Abschicken rechts neben dem Feld, mit
    `help_text` ein Satz darunter, mit dem Feld verknüpft.
    """
    help_id = f"{field.auto_id}-hilfe" if help_text else ""
    context = _textfeld(field, described_by=help_id)
    context.update(button=button, help_text=help_text, help_id=help_id)
    return context


@register.inclusion_tag("core/_datumsfeld.html")
def datumsfeld(field) -> dict:
    """Baustein „Datumsfeld“ (#117, N3): das Datumsfeld des Browsers mit Beschriftung und Fehler am Feld.

    Wie das Textfeld, nur ohne Zahl der Zeichen; das Formular legt das Feld als Datum fest
    (`type="date"`) und mit `max` den letzten wählbaren Tag. Der Browser schickt das Datum immer als
    JJJJ-MM-TT, egal wie er es anzeigt; ein Datum, das er nicht versteht, kommt leer an.
    """
    return _textfeld(field)


@register.inclusion_tag("core/_schalter.html")
def schalter(field) -> dict:
    """Baustein „Schalter“ (#95) für ein Ankreuzfeld eines Formulars, erweitert mit #98 (Regler der Einwilligung).

    Er wirkt erst mit dem Knopf des Dialogs; Vorleseprogramme sagen ihn deshalb als Ankreuzfeld an,
    nicht als Schalter, der sofort schaltet. Titel ist die Beschriftung des Felds, ohne Satz darunter.
    Der Fehler steht rot unter der Zeile und ist mit dem Feld verbunden; nach einem Fehler bleibt er
    gewählt, wie er war. Das Formular legt am Feld fest, zu welchem Formular es gehört (`form`) und
    welchen Wert es schickt (`value`).
    """
    attrs = field.field.widget.attrs
    return {
        "switch": {
            "id": field.auto_id,
            "name": field.html_name,
            "value": attrs.get("value", "on"),
            "title": field.label,
            "checked": bool(field.value()),
            "checkbox": True,
            "error": " ".join(field.errors),
        },
        "form_id": attrs.get("form", ""),
    }


@register.inclusion_tag("core/_antippfeld.html")
def antippfeld(field, saved: str, icon: str, failure: str = "", focus: bool = False) -> dict:
    """Feld zum Antippen (#180, Zielbild „Mein Profil“): in Ruhe wie eine Angabe, angetippt eine Eingabe.

    In Ruhe steht der gespeicherte Wert `saved` (leer: „Noch nicht angegeben“) mit dem Symbol
    `icon` und rechts dem Knopf zum Leeren. Antippen öffnet im selben Rahmen die Eingabe, darunter
    „Verwerfen“ und „Speichern“. Das Öffnen und Schließen macht das Skript (core/static/core/app.js);
    ohne Skript bleiben Eingabe und „Speichern“ wie beim Baustein Textfeld stehen, deshalb
    nutzt es dessen Feld und Fehler. Gespeichert wird immer mit dem Formular drumherum.

    `failure`: Fehlermeldung, wenn das Speichern technisch scheiterte. Sie steht als Meldung direkt
    unter der Eingabe, an der Stelle der Handlung (#186), ist mit der Eingabe verknüpft, und das
    Feld kommt offen vom Server. Mit einem Fehler am Feld ist es ebenso offen, damit die Eingabe
    stehen bleibt. `focus`: Das Feld bekommt beim Laden den Fokus, z. B. gleich nach dem Speichern.
    """
    failure_id = f"{field.auto_id}-meldung"
    context = _textfeld(field, described_by=failure_id if failure else "")
    context.update(saved=saved, icon=icon, open=bool(failure or field.errors), focus=focus, failure=failure,
                   failure_id=failure_id)
    return context


def copyright_years(today=None) -> str:
    """Jahreszahl für den Copyright-Hinweis: „2026“, ab dem Folgejahr „2026–2027“."""
    start = settings.COPYRIGHT_START_YEAR
    current = (today or localdate()).year
    return str(start) if current <= start else f"{start}–{current}"


@register.inclusion_tag("core/_fuss.html")
def fussbereich() -> dict:
    """Fußbereich jeder Seite: Impressum und Datenschutz links, Copyright rechts."""
    return {
        "impressum_url": settings.IMPRESSUM_URL,
        "datenschutz_url": settings.DATENSCHUTZ_URL,
        "holder": settings.COPYRIGHT_HOLDER,
        "years": copyright_years(localdate()),
    }


@register.inclusion_tag("core/_testband.html")
def testumgebung_band() -> dict:
    """Band „Testumgebung“ oben auf jeder Seite, nur wenn die Testumgebung eingeschaltet ist (#58).

    Mit Symbol und Text, nicht nur in Farbe (NFA-03). Als Hinweis (role="note") ohne Fokus,
    damit die Tastatur weiter mit dem ersten Tab zum Inhalt kommt. Gestreift und mit
    Laborsymbol, damit es nicht wie eine Warnmeldung aussieht (#165).
    """
    return {"show": settings.TEST_ENVIRONMENT}
