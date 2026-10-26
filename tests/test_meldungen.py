"""Tests für die Meldungen als gemeinsame Bausteine: Info, Warnung, Fehler, Erfolg (#165, NFA-03).

Die Nummern verweisen auf Sebastians Szenarien zu #165 (26.10.2026, Fassung nach dem Zielbild).
Was nur ein echter Browser zeigen kann (Umbruch am Handy, axe mit Kontrast), prüft der
Rauchtest in rauchtests/test_rauchtest.py. Alle Namen sind erfunden.
"""

import hashlib
import re
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from roles.models import Role

from tests.keycloak_fake import RETURN, keycloak_parameters, login, start_login
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_mein_profil import raw_text, symbols
from tests.test_rollen import build_org, give

pytestmark = pytest.mark.django_db

BASE_DIR = Path(__file__).resolve().parent.parent

HINT_NAME = "Ergänze deinen Namen in deinem DPV-Konto und melde dich danach neu an."
HINT_NO_ORG_BOLD = "Du bist noch keiner Organisation zugeordnet."
HINT_NO_ORG_REST = "Wende dich an die Leitung deiner Gruppe oder deines Stammes, damit sie dich aufnimmt."
HINT_ACCOUNT = (
    "Name und E-Mail-Adresse stammen aus deinem DPV-Konto und lassen sich hier nicht ändern. "
    "Änderungen dort erscheinen hier nach deiner nächsten Anmeldung."
)
HINT_EXPIRED = "Deine Sitzung ist abgelaufen. Bitte melde dich neu an."
HINT_CANCELLED = "Die Anmeldung wurde abgebrochen. Du kannst es noch einmal versuchen."
HINT_UNREACHABLE = "Die Anmeldung ist gerade nicht möglich. Versuche es später noch einmal."
HINT_NO_MAIL = "Die Anmeldung ist nicht möglich, weil in deinem DPV-Konto keine Mail eingetragen ist."

# Je Art: Klasse, Symbol und das Wort, das Vorleseprogramme vorweg ansagen.
KINDS = {
    "info": ("ist-info", "info", "Information:"),
    "warning": ("ist-warnung", "hinweis", "Warnung:"),
    "error": ("ist-fehler", "nein", "Fehler:"),
    "success": ("ist-erfolg", "erfolg", "Erfolg:"),
}


@pytest.fixture
def org():
    """Die Einheiten aus tests/test_rollen.py; Erika und Max haben Mail und noch keine Rolle."""
    o = build_org()
    for user, mail in ((o.erika, "erika.testfrau@example.org"), (o.max, "max.testmann@example.org")):
        user.email = mail
        user.save()
    return o


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def notices(root) -> list:
    """Alle Meldungen einer Seite, in der Reihenfolge der Seite."""
    return _all(root, lambda e: "a-meldung" in _classes(e))


def kind(notice) -> str:
    found = [name for name, (css, _, _) in KINDS.items() if css in _classes(notice)]
    assert len(found) == 1, _classes(notice)
    return found[0]


def spoken_prefix(notice) -> str:
    """Was nur Vorleseprogramme vor der Meldung hören."""
    return _clean(raw_text(_one(_all(notice, lambda e: "sr-nur" in _classes(e)))))


def visible(notice) -> str:
    return _clean(_visible_text(notice))


def notice_with(root, words: str):
    return _one([n for n in notices(root) if words in visible(n)])


def assert_is(notice, expected: str, symbol: str | None = None) -> None:
    """Prüft Art, Symbol und Ansage einer Meldung; das Symbol bleibt für Vorleseprogramme stumm."""
    css, default_symbol, prefix = KINDS[expected]
    assert kind(notice) == expected
    assert symbols(notice) == [symbol or default_symbol]
    assert all(_attr(svg, "aria-hidden") == "true" for svg in _by_tag(notice, "svg"))
    assert spoken_prefix(notice) == prefix


def _profile(user):
    client = Client()
    client.force_login(user)
    return _tree(client.get("/profil/"))


def _login_page(client):
    return _tree(client.get("/anmelden/"))


# ---------- Szenario 1: keiner Organisation zugeordnet ----------


def test_ohne_organisation_warnmeldung_mit_fettem_ersten_satz_als_eigene_zeile(org):
    notice = notice_with(_profile(org.max), HINT_NO_ORG_BOLD)

    assert_is(notice, "warning")
    title = _one(_by_tag(notice, "strong"))
    assert "a-meldung-titel" in _classes(title)
    assert _clean(_visible_text(title)) == HINT_NO_ORG_BOLD
    assert visible(notice) == f"{HINT_NO_ORG_BOLD} {HINT_NO_ORG_REST}"


def test_fest_stehende_meldung_wird_nicht_ungefragt_angesagt(org):
    """Szenario 12 und technische Wahl der Klärung: nur Meldungen nach einer Handlung sind Live-Bereiche."""
    found = notices(_profile(org.max))

    assert len(found) == 2
    for notice in found:
        assert _attr(notice, "role") == "note"
        assert _attr(notice, "aria-live") is None


# ---------- Szenario 2 und 10: Name fehlt ----------


@pytest.mark.parametrize("address", ["/", "/profil/"])
def test_fehlender_name_warnmeldung_ganz_fett(org, address):
    org.max.first_name = ""
    org.max.last_name = ""
    org.max.save()
    client = Client()
    client.force_login(org.max)

    notice = notice_with(_tree(client.get(address)), HINT_NAME)

    assert_is(notice, "warning")
    assert _clean(_visible_text(_one(_by_tag(notice, "strong")))) == HINT_NAME
    assert visible(notice) == HINT_NAME


def test_ohne_namen_und_ohne_organisation_zwei_getrennte_warnmeldungen(org):
    org.max.first_name = ""
    org.max.save()

    found = notices(_profile(org.max))

    assert [kind(n) for n in found] == ["warning", "info", "warning"]
    assert HINT_NAME in visible(found[0]) and HINT_NO_ORG_BOLD not in visible(found[0])
    assert HINT_NO_ORG_BOLD in visible(found[2]) and HINT_NAME not in visible(found[2])


# ---------- Szenario 3: Hinweis zum DPV-Konto ----------


def test_hinweis_zum_dpv_konto_ist_informationsmeldung_mit_schloss(org):
    notice = notice_with(_profile(org.erika), HINT_ACCOUNT)

    assert_is(notice, "info", symbol="schloss")
    assert visible(notice) == HINT_ACCOUNT


def test_mit_vollem_namen_und_organisation_nur_die_informationsmeldung(org):
    give(org.erika, Role.Kind.MEMBER, org.adler)

    assert [kind(n) for n in notices(_profile(org.erika))] == ["info"]


# ---------- Szenarien 4 bis 7: Login-Seite, sofort angesagt ----------


def _assert_live(notice, role: str) -> None:
    assert _attr(notice, "role") == role


def test_abgelaufene_sitzung_informationsmeldung_als_status(client, keycloak):
    login(client)
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))

    root = _tree(client.get("/", follow=True))

    notice = notice_with(root, HINT_EXPIRED)
    assert_is(notice, "info")
    _assert_live(notice, "status")


def test_keycloak_nicht_erreichbar_fehlermeldung_sofort_angesagt(client, keycloak):
    keycloak.unreachable = True
    start_login(client)

    notice = notice_with(_login_page(client), HINT_UNREACHABLE)

    assert_is(notice, "error")
    _assert_live(notice, "alert")


def test_keycloak_bei_der_rueckkehr_nicht_erreichbar_fehlermeldung(client, keycloak):
    state = keycloak_parameters(start_login(client))["state"]
    keycloak.unreachable = True
    client.get(RETURN, {"state": state, "code": "code-nur-test"})

    assert_is(notice_with(_login_page(client), HINT_UNREACHABLE), "error")


def test_abgebrochener_login_fehlermeldung_sofort_angesagt(client, keycloak):
    state = keycloak_parameters(start_login(client))["state"]
    client.get(RETURN, {"state": state, "error": "access_denied"})

    notice = notice_with(_login_page(client), HINT_CANCELLED)

    assert_is(notice, "error")
    _assert_live(notice, "alert")


def test_unzulaessige_angaben_beim_start_fehlermeldung(client):
    client.post("/anmelden/keycloak/start/?scope=openid+fremd")

    assert_is(notice_with(_login_page(client), HINT_CANCELLED), "error")


def test_ohne_mail_warnmeldung_mit_adresse_sofort_angesagt(client, keycloak):
    del keycloak.person["email"]
    login(client)

    notice = notice_with(_login_page(client), HINT_NO_MAIL)

    assert_is(notice, "warning")
    _assert_live(notice, "alert")
    assert settings.ACCOUNT_HELP_EMAIL in visible(notice)


def test_login_seite_ohne_anlass_ohne_meldung(client):
    root = _login_page(client)

    assert notices(root) == []
    assert HINT_EXPIRED not in _clean(_visible_text(root))


# ---------- Szenario 8: Musterseite ----------


def test_musterseite_zeigt_alle_vier_arten_und_den_fehler_am_feld(org):
    client = Client()
    client.force_login(org.erika)
    root = _tree(client.get("/muster/"))

    section = _one(_by_tag(root, "section", aria_labelledby="h-meldungen-bausteine"))
    found = notices(section)
    assert {kind(n) for n in found} == set(KINDS)
    for notice in found:
        assert_is(notice, kind(notice), symbol=symbols(notice)[0])
        assert visible(notice)
    assert [n for n in found if symbols(n) == ["schloss"]], "Informationsmeldung mit passendem Symbol fehlt"
    assert [n for n in found if _by_tag(n, "strong")], "Meldung mit fettem ersten Satz fehlt"
    # Der Fehler am Feld steht gleich darunter im Formular, als rote Schrift unter dem Feld, nicht als Meldung.
    sections = _by_tag(root, "section")
    following = sections[sections.index(section) + 1]
    assert _attr(following, "aria-labelledby") == "h-formular"
    field = _one(_all(following, lambda e: e.name == "input" and _attr(e, "aria-invalid") == "true"))
    error = _one(_by_tag(following, "div", id=_attr(field, "aria-describedby")))
    assert "invalid-feedback" in _classes(error)
    assert notices(following) == [], "Der Fehler am Feld ist keine Meldung der vier Arten"


# ---------- Szenario 12: ohne Farbe am Symbol erkennbar ----------


def test_jede_art_hat_ein_eigenes_symbol_und_ein_eigenes_wort():
    icons = [icon for _, icon, _ in KINDS.values()]
    words = [word for _, _, word in KINDS.values()]

    assert len(set(icons)) == len(icons) and len(set(words)) == len(words)
    drawn = (BASE_DIR / "core" / "templates" / "core" / "_symbole.svg").read_text()
    for icon in [*icons, "labor"]:
        assert f'id="i-{icon}"' in drawn, icon


def test_keine_meldung_mehr_im_aussehen_von_bootstrap():
    """Alle Meldungen nutzen den Baustein; das Türkis und Gelb von Bootstrap kommt nicht mehr vor."""
    templates = [p for p in BASE_DIR.glob("*/templates/**/*.html")]

    assert templates
    for path in templates:
        assert not re.search(r"\balert(-\w+)?\b", path.read_text()), path


# ---------- Szenario 9: Band der Testumgebung ----------


def test_band_der_testumgebung_gestreift_mit_laborsymbol_statt_warndreieck(settings):
    settings.TEST_ENVIRONMENT = True

    root = _tree(Client().get("/anmelden/"))

    band = _one(_all(root, lambda e: "a-testband" in _classes(e)))
    assert symbols(band) == ["labor"]
    assert notices(band) == [] and "a-meldung" not in _classes(band)
    css = (BASE_DIR / "core" / "static" / "core" / "app.css").read_text()
    rule = re.search(r"\.a-testband \{([^}]*)\}", css).group(1)
    assert "var(--akzent)" in rule
    assert "repeating-linear-gradient(-45deg" in rule


def test_sonnengelb_nie_als_flaeche_einer_meldung():
    css = (BASE_DIR / "core" / "static" / "core" / "app.css").read_text()
    rules = re.findall(r"([^{}]*\.(?:a-meldung|ist-(?:info|warnung|fehler|erfolg))(?![\w-])[^{}]*)\{([^}]*)\}", css)

    assert rules
    for selector, body in rules:
        assert "--akzent" not in body, selector


@pytest.mark.parametrize(
    ("css_class", "background", "color"),
    [
        ("ist-info", "--dpv-hauch", "--text"),
        ("ist-warnung", "--warte-grund", "--warte-text"),
        ("ist-fehler", "--ab-grund", "--ab-text"),
        ("ist-erfolg", "--ok-grund", "--ok-text"),
    ],
)
def test_eine_farbfamilie_mit_den_statuskennzeichen(css_class, background, color):
    """Warnung wie „Warteliste“, Fehler wie „abgemeldet“, Erfolg wie „angemeldet“ (Nachklärung, Punkt 2)."""
    css = (BASE_DIR / "core" / "static" / "core" / "app.css").read_text()

    body = re.search(rf"\.a-meldung\.{css_class} \{{([^}}]*)\}}", css).group(1)
    assert f"background: var({background})" in body
    assert f"color: var({color})" in body


# ---------- Zielbild und Doku ----------

TARGET_IMAGES = BASE_DIR / "docs" / "zielbilder"


def test_zielbild_meldungen_liegt_unveraendert_mit_eintrag_im_repo():
    image = TARGET_IMAGES / "meldungen.html"
    readme = (TARGET_IMAGES / "README.md").read_text()

    checksum = hashlib.sha256(image.read_bytes()).hexdigest()
    assert checksum == "b0b5ad4a3071dbe24ad071236aa010887ae4b955fbe11e49ae73d00e9cb70498"
    section = readme.split("## Meldungen", 1)[1]
    assert checksum in section
    for must in ("26.10.2026", "Orientierung, keine Anforderung", "Abweichungen", "#165"):
        assert must in section, must


def test_zielbild_meldungen_laedt_nichts_von_fremden_servern():
    content = (TARGET_IMAGES / "meldungen.html").read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    # Nur die Hilfeadresse des Tools, keine Adresse einer Person.
    assert set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content)) == {"anmeldetool@dpvonline.de"}


def test_regel_steht_in_der_gestaltung_und_in_den_entscheidungen():
    design = (BASE_DIR / "docs" / "gestaltung.md").read_text()
    decisions = (BASE_DIR / "docs" / "entscheidungen.md").read_text()

    for word in ("Informationsmeldung", "Warnmeldung", "Fehlermeldung", "Erfolgsmeldung", "Fehler am Feld",
                 "Statuskennzeichen", "#165"):
        assert word in design, word
    assert "nie für Meldungen" in design
    entry = decisions.split("(#165)", 1)
    assert len(entry) == 2, "Eintrag zu #165 fehlt"
    assert "Sonnengelb" in entry[1].split("\n## ", 1)[0]
