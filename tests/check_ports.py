"""Feste Ports der Prüfungen, getrennt von denen des eigenen Tools (#167).

Port 8000 und 8081 gehören Sebastian: das Tool aus README Schritt 9 und die eigene
Testumgebung im Container (README, Schritt T). Die Prüfungen nutzen eigene Ports, damit beides
gleichzeitig laufen kann. Zwei Prüfläufe gleichzeitig gehen weiter nicht: Sie teilen sich die
Testdatenbank und diese Ports.

Ohne Django, damit es auch die Prüfung der Testumgebung im Container (containertests/) nutzen kann.
"""

import socket

# Das Tool im Rauchtest (rauchtests/).
SMOKE_TEST_PORT = 8010
# Tool und Keycloak der Testumgebung in der Container-Prüfung (containertests/).
CONTAINER_TOOL_PORT = 8020
CONTAINER_KEYCLOAK_PORT = 8091


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
