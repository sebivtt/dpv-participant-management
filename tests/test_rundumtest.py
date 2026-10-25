"""Rundumtest: Jede Adresse verlangt einen Login, außer den Login-Seiten (#5, CONTRIBUTING.md, Abschnitt 4).

Geht alle Adressen des Tools durch, auch solche, die später dazukommen. Eine neue Adresse
ist ohne eigenes Zutun geschützt; wer sie öffentlich machen will, muss sie hier eintragen
und begründen. Seit #90 muss außerdem jede Adresse markiert sein: „prüft Rechte“ mit den
Kennungen ihrer Zeilen in der Rechtematrix oder „enthält keine Personendaten“ mit Begründung
(`access/addresses.py`). Und kein Code außerhalb der zentralen Rechteprüfung liest Personen-
oder Anmeldedaten selbst aus der Datenbank.
"""

import ast
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RoutePattern

from access.addresses import checks_rights, without_personal_data
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


def _example_address(pattern: str) -> str:
    """Macht aus einem Muster wie anmelden/<str:provider_id>/start/ eine aufrufbare Adresse."""
    address = re.sub(r"<(?:\w+:)?\w+>", "1", pattern)
    address = re.sub(r"\(\?P<\w+>[^)]*\)", "1", address).lstrip("^").rstrip("$")
    return "/" + address


ALL = list(_all_patterns(get_resolver().url_patterns))


def test_rundumtest_findet_die_adressen_des_tools():
    names = {entry.name for _pattern, entry in ALL}
    assert {"start", *PUBLIC} <= names


def test_nur_die_login_seiten_sind_als_oeffentlich_markiert():
    public = {entry.name for _pattern, entry in ALL if getattr(entry.callback, "login_required", True) is False}

    assert public == PUBLIC


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


# Personen- und Anmeldedaten nur über die zentrale Rechteprüfung (#90, CONTRIBUTING.md, Abschnitt 4)

# Modelle mit Personen- oder Anmeldedaten. Kommen neue dazu (verwaltete Personen, Anmeldungen),
# gehören sie hierher.
PERSONAL_MODELS = {"User", "Role", "RoleChange", "get_user_model()"}
# Wo Lesen an der zentralen Stelle vorbei erlaubt ist, mit Begründung.
ALLOWED_FILES = {
    # Die zentrale Rechteprüfung selbst.
    "access/rights.py",
    # Die Regeln beim Speichern und Löschen einer Rolle; sie zeigen nichts an.
    "roles/models.py",
    # Befehle auf dem Server, außerhalb des Tools (Rechtematrix, „Außerhalb des Tools“).
    "roles/management/commands/admin.py",
}
# Abfragen über einen Verweis auf Rollen oder Konten, z. B. filter(roles__user=…), order_by("-user__email").
LOOKUP_THROUGH_PERSONS = re.compile(r"^-?(roles|user)__\w+")
APP_FOLDERS = ("access", "accounts", "config", "core", "roles", "units")


def bypasses(source: str) -> list[str]:
    """Stellen im Quelltext, die Personen- oder Anmeldedaten selbst aus der Datenbank lesen.

    Erkannt werden die üblichen Wege: `Modell.objects`, die anderen Manager-Namen, die
    Rollen über ein Konto (`.roles`), rohes SQL (`.raw(`, `cursor(`) und Abfragen über einen
    Verweis auf Rollen oder Konten (`roles__`, `user__`). Ein Test kann nicht jeden denkbaren
    Weg erkennen; was er nicht erkennt, bleibt Sache der unabhängigen Prüfung.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute):
            owner = ast.unparse(node.value)
            if node.attr in ("objects", "_default_manager", "_base_manager") and owner in PERSONAL_MODELS:
                found.append(f"{owner}.{node.attr}")
            elif node.attr == "roles" or node.attr in ("raw", "cursor"):
                found.append(f"{owner}.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if LOOKUP_THROUGH_PERSONS.match(node.value):
                found.append(node.value)
        elif isinstance(node, ast.keyword) and node.arg and LOOKUP_THROUGH_PERSONS.match(node.arg):
            found.append(node.arg)
    return found


def app_files() -> list[Path]:
    root = Path(settings.BASE_DIR)
    return sorted(
        path
        for folder in APP_FOLDERS
        for path in (root / folder).rglob("*.py")
        if "migrations" not in path.parts
    )


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
    ],
)
def test_lesen_vorbei_an_der_zentralen_stelle_wird_erkannt(source):
    assert bypasses(source)


def test_lesen_von_einheiten_ist_kein_lesen_von_personendaten():
    """Gegenprobe: Namen von Einheiten sind keine Personendaten (BER-01)."""
    assert bypasses("Unit.objects.filter(kind='troop').values_list('name')") == []
