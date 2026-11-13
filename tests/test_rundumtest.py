"""Rundumtest: Jede Adresse verlangt einen Login, außer den Login-Seiten (#5, CONTRIBUTING.md, Abschnitt 4).

Geht alle Adressen des Tools durch, auch solche, die später dazukommen. Eine neue Adresse
ist ohne eigenes Zutun geschützt; wer sie öffentlich machen will, muss sie hier eintragen
und begründen. Seit #90 muss außerdem jede Adresse markiert sein: „prüft Rechte“ mit den
Kennungen ihrer Zeilen in der Rechtematrix oder „enthält keine Personendaten“ mit Begründung
(`access/addresses.py`). Und kein Code außerhalb der zentralen Rechteprüfung liest Personen-
oder Anmeldedaten selbst aus der Datenbank. Seit #64 nehmen Adressen mit Login Einträge nur über
ihre zufällige Kennung (`<key:…>`), nie über eine laufende Nummer. Seit #156 hat jede Adresse mit
Kennung einen Test „genau gleich wie nicht vorhanden“; die Suche nach Nummern in den Antworten
steht in `tests/test_rechte_ohne_seite.py`, weil sie dessen Aufrufe aller Adressen nutzt.
"""

import ast
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RoutePattern

from access.addresses import checks_rights, without_personal_data
from access.keys import KEY_CONVERTER, KEY_LENGTH, has_key
from tests import urls as test_urls
from tests.rechtematrix import matrix_text, row_ids

# Die einzigen Adressen, die ohne Login antworten dürfen, mit Begründung.
PUBLIC = {
    # Die Login-Seite selbst.
    "account_login",
    # Start und Rückkehr des Logins bei Keycloak; davor ist noch niemand angemeldet.
    "openid_connect_login",
    "openid_connect_callback",
    # Abmelden auch ohne gültige Sitzung, damit nach abgelaufener Sitzung die Abmeldung
    # bei Keycloak trotzdem gelingt. Geschützt durch den Formularschutz (CSRF).
    "account_logout",
}


def _all_patterns(patterns, prefix: str = ""):
    """Liefert jede Adresse des Tools als (Muster, Eintrag), auch aus eingebundenen Listen."""
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _all_patterns(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry


# Steht für jede Kennung (`<key:…>`) in einer Beispieladresse; zu ihr gehört kein Eintrag.
EXAMPLE_KEY = "a" * KEY_LENGTH


def _example_address(pattern: str) -> str:
    """Macht aus einem Muster wie anmelden/<str:provider_id>/start/ eine aufrufbare Adresse."""
    address = re.sub(rf"<{KEY_CONVERTER}:\w+>", EXAMPLE_KEY, pattern)
    address = re.sub(r"<(?:\w+:)?\w+>", "1", address)
    address = re.sub(r"\(\?P<\w+>[^)]*\)", "1", address).lstrip("^").rstrip("$")
    return "/" + address


ALL = list(_all_patterns(get_resolver().url_patterns))


def test_rundumtest_findet_die_adressen_des_tools():
    names = {entry.name for _pattern, entry in ALL}
    assert {"start", *PUBLIC} <= names


def test_nur_die_login_seiten_sind_als_oeffentlich_markiert():
    public = {entry.name for _pattern, entry in ALL if getattr(entry.callback, "login_required", True) is False}

    assert public == PUBLIC


@pytest.mark.alle_adressen
@pytest.mark.django_db
@pytest.mark.parametrize(("pattern", "entry"), [p for p in ALL if p[1].name not in PUBLIC], ids=lambda p: str(p))
def test_jede_andere_adresse_leitet_ohne_login_zum_login(client, pattern, entry):
    address = _example_address(pattern)

    for method in (client.get, client.post):
        response = method(address)
        assert response.status_code == 302, f"{address} antwortet ohne Login mit {response.status_code}"
        assert response["Location"].startswith("/anmelden/?next=")


# Markierung jeder Adresse (#90): prüft Rechte oder enthält keine Personendaten


def unmarked(patterns) -> list[str]:
    """Adressen ohne Markierung oder mit beiden Markierungen zugleich."""
    found = []
    for pattern, entry in patterns:
        rows = getattr(entry.callback, "rights_rows", None)
        reason = getattr(entry.callback, "no_personal_data", None)
        if bool(rows) == bool(reason):
            found.append(pattern)
    return found


def test_jede_adresse_ist_markiert():
    assert unmarked(ALL) == []


def test_unmarkierte_adresse_macht_den_rundumtest_rot():
    """Gegenprobe: eine neue Adresse ohne Markierung und eine mit beiden."""

    def plain(request):
        return None

    both = checks_rights("PK-01")(without_personal_data("Begründung")(lambda request: None))

    patterns = [("neu/", URLPattern(RoutePattern("neu/"), plain)), ("beide/", URLPattern(RoutePattern("beide/"), both))]

    assert unmarked(patterns) == ["neu/", "beide/"]


def test_markierungen_nennen_vorhandene_zeilen_der_rechtematrix():
    known = row_ids(matrix_text())
    named = {row for _pattern, entry in ALL for row in getattr(entry.callback, "rights_rows", ())}

    assert named
    assert named <= known


@pytest.mark.parametrize("rows", [(), ("",), ("PK-1",), ("pk-01",), ("PK-01", None)])
def test_markierung_ohne_gueltige_kennung_wird_abgelehnt(rows):
    with pytest.raises(ValueError, match="Kennung"):
        checks_rights(*rows)


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_markierung_ohne_begruendung_wird_abgelehnt(reason):
    with pytest.raises(ValueError, match="Begründung"):
        without_personal_data(reason)


# Einträge in Adressen nur über ihre zufällige Kennung (#64)

PARAMETER = re.compile(r"<(?:(\w+):)?\w+>|\(\?P<\w+>")


def numbered_addresses(patterns) -> list[str]:
    """Adressen mit Login, die eine andere Angabe als eine Kennung nehmen, z. B. <int:pk> oder <str:name>."""
    found = []
    for pattern, entry in patterns:
        if entry.name in PUBLIC:
            continue
        if any(match.group(1) != KEY_CONVERTER for match in PARAMETER.finditer(pattern)):
            found.append(pattern)
    return found


def test_adressen_mit_login_nehmen_eintraege_nur_ueber_ihre_kennung():
    assert numbered_addresses(ALL) == []


def test_laufende_nummer_in_einer_adresse_macht_den_rundumtest_rot():
    """Gegenprobe: Nummer, Text, UUID und regulärer Ausdruck fallen auf, die Kennung nicht."""

    def view(request):
        return None

    patterns = [
        (route, URLPattern(RoutePattern(route), view, name=f"neu{number}"))
        for number, route in enumerate(
            ["person/<int:pk>/", "person/<str:name>/", "person/<uuid:id>/", "person/<pk>/", "einheit/<key:unit>/"]
        )
    ]
    patterns.append((r"^alt/(?P<pk>\d+)/$", patterns[0][1]))

    assert numbered_addresses(patterns) == [
        "person/<int:pk>/", "person/<str:name>/", "person/<uuid:id>/", "person/<pk>/", r"^alt/(?P<pk>\d+)/$"
    ]


# Jede Adresse mit Kennung hat einen Test „genau gleich wie nicht vorhanden“ (#156, Lücke L3 aus #64)

TESTS = Path(settings.BASE_DIR) / "tests"
# Der Baustein aus tests/test_nicht_gefunden.py: vergleicht die ganze Antwort mit der für eine erfundene Kennung.
LIKE_MISSING = "assert_like_missing"
LIKE_MISSING_MARK = "pytest.mark.wie_nicht_vorhanden"
# Übersprungene oder als bekannter Fehler markierte Tests belegen nichts.
NOT_RUN = {"pytest.mark.skip", "pytest.mark.skipif", "pytest.mark.xfail"}


def sources_of_tests() -> list[str]:
    """Der Quelltext jeder Testdatei, auch in Unterordnern; fremder Code unter `vendor` zählt nicht."""
    return [path.read_text(encoding="utf-8") for path in sorted(TESTS.rglob("*.py")) if "vendor" not in path.parts]


def addresses_tested_like_missing(sources: list[str]) -> set[str]:
    """Muster der Adressen, deren verbotenen Fall ein Test mit dem Vergleich „wie nicht vorhanden“ prüft.

    Zählt nur ein Test mit `@pytest.mark.wie_nicht_vorhanden("muster")`, der `assert_like_missing`
    aufruft und nicht übersprungen wird. Ob er den richtigen verbotenen Fall wählt, bleibt Sache der unabhängigen Prüfung.
    """
    found = set()
    for source in sources:
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            compares = any(isinstance(call, ast.Call) and ast.unparse(call.func) == LIKE_MISSING for call in ast.walk(node))
            marks = {ast.unparse(decorator.func if isinstance(decorator, ast.Call) else decorator) for decorator in node.decorator_list}
            if not compares or marks & NOT_RUN:
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and ast.unparse(decorator.func) == LIKE_MISSING_MARK:
                    found |= {arg.value for arg in decorator.args if isinstance(arg, ast.Constant)}
    return found


def keyed_without_like_missing_test(patterns, sources: list[str]) -> list[str]:
    """Adressen mit Kennung (`<key:…>`) ohne Test „genau gleich wie nicht vorhanden“."""
    tested = addresses_tested_like_missing(sources)
    return [pattern for pattern, _entry in patterns if has_key(pattern) and pattern not in tested]


def test_jede_adresse_mit_kennung_hat_einen_test_wie_nicht_vorhanden():
    """V8: auch für Adressen, die später dazukommen (G3). Regel in CONTRIBUTING.md, Abschnitt 4."""
    assert keyed_without_like_missing_test(ALL, sources_of_tests()) == []


def test_adresse_mit_kennung_ohne_passenden_test_macht_den_rundumtest_rot():
    """Gegenprobe zu V8: ohne Markierung, mit Markierung ohne den Vergleich, mit Markierung für eine andere Adresse, übersprungen."""

    def view(request):
        return None

    routes = ["neu/<key:person>/", "ohne-vergleich/<key:person>/", "andere/<key:person>/", "uebersprungen/<key:person>/", "ohne-kennung/"]
    patterns = [(route, URLPattern(RoutePattern(route), view)) for route in routes]
    sources = [
        """
@pytest.mark.wie_nicht_vorhanden("ohne-vergleich/<key:person>/")
def test_ohne_vergleich(org):
    assert answers(org.falke, "/ohne-vergleich/x/")[0][0] == 404

@pytest.mark.wie_nicht_vorhanden("woanders/<key:person>/")
def test_andere_adresse(org):
    assert_like_missing(org.falke, "/woanders/x/")

def test_ohne_markierung(org):
    assert_like_missing(org.falke, "/andere/x/")

@pytest.mark.skip(reason="später")
@pytest.mark.wie_nicht_vorhanden("uebersprungen/<key:person>/")
def test_uebersprungen(org):
    assert_like_missing(org.falke, "/uebersprungen/x/")
"""
    ]

    assert keyed_without_like_missing_test(patterns, sources) == routes[:4]


def test_adresse_mit_kennung_und_passendem_test_bleibt_gruen():
    """G3: Die Testadressen mit Kennung aus tests/urls.py haben ihre Tests in tests/test_nicht_gefunden.py."""
    patterns = [(pattern, entry) for pattern, entry in _all_patterns(test_urls.urlpatterns) if pattern.startswith("test/")]

    assert [pattern for pattern, _entry in patterns if has_key(pattern)]
    assert keyed_without_like_missing_test(patterns, sources_of_tests()) == []


def test_beispieladresse_setzt_eine_kennung_in_der_richtigen_form_ein():
    assert _example_address("einheit/<key:unit>/person/<key:person>/") == f"/einheit/{EXAMPLE_KEY}/person/{EXAMPLE_KEY}/"


# Personen- und Anmeldedaten nur über die zentrale Rechteprüfung (#90, CONTRIBUTING.md, Abschnitt 4)

# Modelle mit Personen- oder Anmeldedaten, auch die Protokolle (Namen der Urheber) und die Daten
# des Logins (TD-01). Kommen neue dazu (verwaltete Personen, Anmeldungen), gehören sie hierher.
PERSONAL_MODELS = {
    "User",
    "get_user_model()",
    "Role",
    "RoleChange",
    "UnitChange",
    "Session",
    "SocialAccount",
    "SocialToken",
    "EmailAddress",
    # Wer wann über die genaue Mail oder den Benutzernamen gesucht hat (PK-24, #190).
    "AccountSearch",
    # Verwaltete Personen (#117) und ihre angezeigten Leitungsrollen (#99).
    "ManagedPerson",
    "DisplayedLead",
    # Veranstaltungen mit ihrer Veranstaltungsleitung (#100).
    "Event",
}
# Wo Lesen an der zentralen Stelle vorbei erlaubt ist, mit Begründung.
ALLOWED_FILES = {
    # Die zentrale Rechteprüfung selbst.
    "access/rights.py",
    # Die Regeln beim Speichern und Löschen einer Rolle; sie zeigen nichts an.
    "roles/models.py",
    # Die Regeln beim Speichern verwalteter Personen und ihrer angezeigten Leitungsrollen, auch beim
    # Ringwechsel eines Stammes (#99). Namen stehen nur in Ablehnungen für Leitungen, die die Person ohnehin
    # sehen (unabhängige Prüfung, Befund B3); wie bei roles/models.py.
    "persons/models.py",
    # Der Abgleich mit Keycloak beim Login: ändert nur das Konto, das sich gerade anmeldet,
    # und zeigt nichts an (#76).
    "accounts/keycloak_abgleich.py",
    # Befehle auf dem Server, außerhalb des Tools (Rechtematrix, „Außerhalb des Tools“).
    "roles/management/commands/admin.py",
    "roles/management/commands/federation_lead.py",
    # Der Befehl für Testdaten (#103): läuft nur lokal und in der Testumgebung, leert die Datenbank bis auf die
    # Konten und zeigt höchstens Benutzernamen an; verwaltete Personen legt er über die zentrale Stelle an.
    "core/management/commands/testdata.py",
    # Der Zusatz des Befehls für den Leistungstest (#104): schreibt erfundene Massendaten in einem Rutsch an der
    # zentralen Stelle vorbei (docs/entscheidungen.md, 13.11.2026, #104) und zeigt höchstens Benutzernamen an.
    "core/management/mass_data.py",
}
# Abfragen über einen Verweis auf Rollen, Konten, verwaltete Personen (#117) oder Veranstaltungen (#100), auch über mehrere Stufen, z. B.
# filter(roles__user=…), order_by("-user__email"), filter(parent__roles__kind=…),
# prefetch_related("roles"). Ein bloßes "roles" oder "user" zählt nur als Angabe an eine Abfrage;
# sonst heißen so auch die App und das Konto der Anfrage.
LOOKUP_THROUGH_PERSONS = re.compile(
    r"(^-?|__)(roles|user|managed_persons|displayed_leads|led_events)__\w"
    r"|__(roles|user|managed_persons|displayed_leads|led_events)$")
QUERY_METHODS = {"select_related", "prefetch_related", "values", "values_list", "only", "order_by", "annotate"}
# Ordner, die nur Tests enthalten; jeder andere Python-Ordner gehört zum Tool und wird durchsucht.
ONLY_FOR_TESTS = {"tests", "rauchtests", "containertests"}


def bypasses(source: str) -> list[str]:
    """Stellen im Quelltext, die Personen- oder Anmeldedaten selbst aus der Datenbank lesen.

    Erkannt werden die üblichen Wege: `Modell.objects`, die anderen Manager-Namen, die
    Rollen über ein Konto (`.roles`), rohes SQL (`.raw(`, `cursor(`) und Abfragen über einen
    Verweis auf Rollen oder Konten (`roles__`, `user__`, auch über mehrere Stufen). Ein Test kann
    nicht jeden denkbaren Weg erkennen, z. B. kein umbenanntes Modell (`import User as U`); was
    er nicht erkennt, bleibt Sache der unabhängigen Prüfung.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute):
            owner = ast.unparse(node.value)
            if node.attr in ("objects", "_default_manager", "_base_manager") and owner in PERSONAL_MODELS:
                found.append(f"{owner}.{node.attr}")
            elif node.attr in ("roles", "managed_persons", "led_events") or node.attr in ("raw", "cursor"):
                found.append(f"{owner}.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if LOOKUP_THROUGH_PERSONS.search(node.value):
                found.append(node.value)
        elif isinstance(node, ast.keyword) and node.arg and LOOKUP_THROUGH_PERSONS.search(node.arg):
            found.append(node.arg)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in QUERY_METHODS:
            found += [f"{node.func.attr}({arg.value!r})" for arg in node.args if _names_persons(arg)]
    return found


def _names_persons(arg: ast.expr) -> bool:
    return isinstance(arg, ast.Constant) and arg.value in ("roles", "user", "-user", "managed_persons")


def app_folders() -> set[str]:
    """Jeder Python-Ordner des Tools, auch einer, der erst später dazukommt."""
    root = Path(settings.BASE_DIR)
    return {path.parent.name for path in root.glob("*/__init__.py")} - ONLY_FOR_TESTS


def app_files() -> list[Path]:
    root = Path(settings.BASE_DIR)
    return sorted(
        path
        for folder in app_folders()
        for path in (root / folder).rglob("*.py")
        if "migrations" not in path.parts
    )


def test_jeder_ordner_des_tools_wird_durchsucht():
    """Gegenprobe: Ein neuer Ordner fällt nicht still aus der Suche heraus."""
    assert {"access", "accounts", "config", "core", "roles", "units"} <= app_folders()
    assert not ONLY_FOR_TESTS & app_folders()


def test_niemand_liest_personendaten_an_der_zentralen_stelle_vorbei():
    root = Path(settings.BASE_DIR)
    found = {}
    for path in app_files():
        relative = path.relative_to(root).as_posix()
        if relative in ALLOWED_FILES:
            continue
        hits = bypasses(path.read_text(encoding="utf-8"))
        if hits:
            found[relative] = hits

    assert found == {}


def test_ausnahmen_gibt_es_noch():
    """Eine Ausnahme für eine gelöschte Datei fiele sonst still weg und gälte für eine neue."""
    root = Path(settings.BASE_DIR)

    assert all((root / name).is_file() for name in ALLOWED_FILES)


@pytest.mark.parametrize(
    "source",
    [
        "User.objects.filter(pk=1)",
        "get_user_model().objects.all()",
        "Role._default_manager.all()",
        "RoleChange.objects.all()",
        "request.user.roles.all()",
        "Unit.objects.filter(roles__user=1)",
        "Unit.objects.values('roles__user__email')",
        "Unit.objects.order_by('-roles__kind')",
        "Unit.objects.raw('SELECT 1')",
        "connection.cursor()",
        "UnitChange.objects.all()",
        "Session.objects.all()",
        "SocialAccount.objects.all()",
        "SocialToken.objects.all()",
        "EmailAddress.objects.all()",
        "Unit.objects.filter(parent__roles__user=1)",
        "Unit.objects.filter(children__roles__kind='member')",
        "Unit.objects.prefetch_related('roles')",
        "Unit.objects.values('roles')",
        "Unit.objects.filter(roles__user__email='x')",
        # Verwaltete Personen über ihre Organisation (#117, unabhängige Prüfung, Befund 4).
        "unit.managed_persons.all()",
        "Unit.objects.filter(managed_persons__first_name='Lena')",
        "Unit.objects.prefetch_related('managed_persons')",
        # Veranstaltungen und die eigenen Veranstaltungen eines Kontos (#100).
        "Event.objects.all()",
        "request.user.led_events.all()",
        "Unit.objects.filter(roles__user__led_events__name='x')",
        "get_user_model().objects.values('led_events__name')",
    ],
)
def test_lesen_vorbei_an_der_zentralen_stelle_wird_erkannt(source):
    assert bypasses(source)


def test_lesen_von_einheiten_ist_kein_lesen_von_personendaten():
    """Gegenprobe: Namen von Einheiten sind keine Personendaten (BER-01)."""
    assert bypasses("Unit.objects.filter(kind='troop').values_list('name')") == []


def test_app_namen_und_das_konto_der_anfrage_sind_kein_lesen():
    """Gegenprobe: So heißen auch die App „roles“ und das Konto der Anfrage."""
    assert bypasses("INSTALLED_APPS = ['roles']\nname = 'roles'\ngetattr(request, 'user', None)") == []
