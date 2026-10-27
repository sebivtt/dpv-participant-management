"""Feste Ports der Prüfungen, getrennt von denen des eigenen Tools (#167).

Port 8000 und 8081 gehören Sebastian: das Tool aus README Schritt 9 und die eigene
Testumgebung im Container (README, Schritt T). Die Prüfungen nutzen eigene Ports, damit beides
gleichzeitig laufen kann.

Zwei Prüfläufe aus verschiedenen Arbeitskopien dürfen gleichzeitig laufen (#184): Jede hat ihre
eigene Test-Datenbank (config/settings.py). Rauchtest und Container-Prüfung brauchen aber diese
festen Ports; dort wartet ein zweiter Lauf, bis der erste fertig ist (wait_for_turn).

Ohne Django, damit es auch die Prüfung der Testumgebung im Container (containertests/) nutzen kann.
"""

import socket
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

# Das Tool im Rauchtest (rauchtests/).
SMOKE_TEST_PORT = 8010
# Tool und Keycloak der Testumgebung in der Container-Prüfung (containertests/).
CONTAINER_TOOL_PORT = 8020
CONTAINER_KEYCLOAK_PORT = 8091

# Wartesperren für Rauchtest und Container-Prüfung (#184): Diesen Port belegt nur der Prüflauf,
# der gerade dran ist. Das Betriebssystem gibt ihn frei, sobald der Lauf endet, auch nach
# einem Absturz; eine Sperre bleibt so nie hängen.
SMOKE_TEST_LOCK_PORT = 8019
CONTAINER_LOCK_PORT = 8029
# So lange wartet ein Lauf höchstens auf einen anderen (Sebastian, Klärung von #184).
WAIT_FOR_OTHER_CHECK_SECONDS = 30 * 60
# So lange darf ein Prüf-Port nach dem vorigen Lauf noch belegt sein (rund 30 Sekunden, #167).
PORT_RELEASE_SECONDS = 90


def is_busy(port: int) -> bool:
    """Sagt, ob ein Programm den Port auf diesem Rechner belegt.

    Zwei Proben, weil jede eine Lücke hat: Antwortet dort etwas, ist er belegt. Antwortet
    nichts, kann er trotzdem belegt sein, etwa noch rund 30 Sekunden nach dem Ende einer
    Container-Prüfung auf dem Mac (#167); das zeigt erst der Versuch, ihn selbst zu belegen.
    Belegt wird dabei so wie vom Tool im Rauchtest, das einen eben freigegebenen Port sofort
    wieder nehmen darf (SO_REUSEADDR), damit ein gerade beendeter eigener Lauf nicht stört.
    """
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            return True
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return True
    return False


def busy_port_message(port: int, purpose: str) -> str:
    """Meldung für einen belegten Prüf-Port: welcher Port, wofür, und was zu tun ist."""
    return (
        f"Port {port} ist belegt; die Prüfung braucht ihn für {purpose}. Meist läuft noch eine "
        "andere Prüfung (./pruefen.sh) oder ihr Container räumt gerade auf: eine Minute warten und "
        f"neu starten. Welches Programm den Port belegt, zeigt im Terminal: lsof -i :{port}"
    )


def fail_if_busy(port: int, purpose: str, seconds: float = 0) -> None:
    """Bricht die Prüfung mit busy_port_message ab, wenn der Port belegt ist.

    Sonst scheiterte sie später mit „Address already in use“ oder „port is already allocated“.
    Mit seconds wartet sie vorher so lange, ob er frei wird, etwa nach dem vorigen Prüflauf.
    """
    deadline = time.monotonic() + seconds
    while is_busy(port):
        if time.monotonic() >= deadline:
            pytest.fail(busy_port_message(port, purpose))
        time.sleep(0.5)


@contextmanager
def wait_for_turn(
    lock_port: int,
    purpose: str,
    say: Callable[[str], None],
    seconds: float = WAIT_FOR_OTHER_CHECK_SECONDS,
    pause: float = 2,
) -> Iterator[None]:
    """Lässt die Prüfung erst laufen, wenn kein anderer Prüflauf gerade dort ist (#184).

    Die Sperre ist der Port lock_port: Wer ihn belegt, ist dran. Die anderen warten, melden das
    einmal mit say und brechen nach seconds mit einer Meldung ab, was zu tun ist.
    """
    deadline = time.monotonic() + seconds
    waiting = False
    while True:
        lock = socket.socket()
        try:
            lock.bind(("127.0.0.1", lock_port))
            break
        except OSError:
            lock.close()
        if not waiting:
            say(f"Warte auf eine andere Prüfung ({purpose}) …")
            waiting = True
        if time.monotonic() >= deadline:
            pytest.fail(
                f"Eine andere Prüfung ({purpose}) ist nach {round(seconds / 60)} Minuten Warten nicht fertig. "
                "Läuft in einem anderen Terminal oder einer anderen Session noch ./pruefen.sh, sie abwarten oder "
                f"beenden und dann neu starten. Welches Programm gerade dran ist, zeigt im Terminal: lsof -i :{lock_port}"
            )
        time.sleep(pause)
    try:
        yield
    finally:
        lock.close()


def tell(config: pytest.Config) -> Callable[[str], None]:
    """Gibt einen Text sofort im Terminal aus, auch während pytest die Ausgabe sonst zurückhält."""
    capture = config.pluginmanager.getplugin("capturemanager")

    def say(text: str) -> None:
        with capture.global_and_fixture_disabled():
            sys.stdout.write("\n" + text + "\n")
            sys.stdout.flush()

    return say
