"""Katalogtests: Tests, die den Bausteinkatalog unter /bausteine/ aufrufen (#304).

Jeder solche Test trägt das Kennzeichen ``@pytest.mark.bausteinkatalog``. Der schnelle Lauf
(``./pruefen.sh schnell``) nimmt alle so gekennzeichneten Tests immer mit, auch wenn ihre Datei
nicht genannt ist: Eine Änderung an einem gemeinsamen Baustein ändert den Katalog, und dessen
Tests stehen in vielen Dateien.

Gerüst: Kennzeichen und Option sind bekannt, wirken aber noch nicht.
"""

MARK = "bausteinkatalog"
OPTION = "--schnelle-auswahl"
CATALOG = "/bausteine/"


def catalog_requested() -> bool:
    """Ob der laufende Test den Katalog aufgerufen hat (Gerüst: noch nie)."""
    return False


def pytest_addoption(parser):
    parser.addoption(
        OPTION,
        default=None,
        metavar="DATEIEN",
        help="Schneller Lauf (pruefen.sh): nur die Tests dieser Dateien (durch Leerzeichen getrennt) und alle Katalogtests.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", f"{MARK}: Test ruft den Bausteinkatalog auf; läuft im schnellen Lauf immer mit (#304)")
