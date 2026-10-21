"""Der Webserver gunicorn schreibt keine Adressen, IP-Adressen oder Meldungstexte ins Log (#58).

gunicorn hat ein eigenes Log neben dem von Django. Ohne Vorkehrung schriebe es bei einer
ungültigen Anfrage die Anfragezeile mit IP-Adresse und bei einem Fehler im Webserver die
echte Adresse mit Parametern ins Log, etwa den Login-Code von Keycloak. Das verbietet die
Entscheidung zu #6 (Punkte 3 bis 5). Gefunden von der unabhängigen Prüfung zu #58.

Geprüft wird mit derselben Einstellungsdatei wie im Container (docker/gunicorn.conf.py),
mit einem echten gunicorn in einem eigenen Prozess. Alle Daten sind erfunden.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "docker" / "gunicorn.conf.py"

SECRETS = ("/konto/17", "erika", "example.org", "ip=", "geheim", "Invalid request", "Error handling")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _send(port: int, raw: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=10) as connection:
        connection.sendall(raw)
        chunks = []
        while chunk := connection.recv(65536):
            chunks.append(chunk)
        return b"".join(chunks)


def _log_of_gunicorn(app: str, raw: bytes) -> tuple[str, bytes]:
    """Startet gunicorn mit der Einstellungsdatei des Containers, schickt eine Anfrage und gibt Log und Antwort zurück."""
    port = _free_port()
    process = subprocess.Popen(  # noqa: S603 -- fester Befehl mit dem eigenen Python, keine Eingaben von außen
        [sys.executable, "-m", "gunicorn", "-c", str(CONFIG), "--bind", f"127.0.0.1:{port}", "--workers", "1", app],
        cwd=BASE_DIR,
        env={"PATH": os.environ.get("PATH", "")},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                assert time.monotonic() < deadline, "gunicorn startet nicht"
                assert process.poll() is None, process.communicate()[0]
                time.sleep(0.2)
        answer = _send(port, raw)
    finally:
        process.terminate()
        log, _ = process.communicate(timeout=30)
    return log, answer


def _assert_nothing_from_the_request(log: str) -> None:
    for secret in SECRETS:
        assert secret not in log, (secret, log)


def test_ungueltige_anfrage_steht_ohne_anfragezeile_und_ohne_ip_im_log():
    log, answer = _log_of_gunicorn("tests.webserver_apps:ok", b"GET /konto/17/?mail=erika@example.org\r\n\r\n")

    assert answer.startswith(b"HTTP/1.1 400")
    assert "Ungültige Anfrage (Webserver)" in log
    _assert_nothing_from_the_request(log)


def test_fehler_im_webserver_steht_nur_mit_seiner_art_im_log():
    raw = (
        b"GET /konto/17/?code=erfunden&mail=erika@example.org HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
    )

    log, answer = _log_of_gunicorn("tests.webserver_apps:failing", raw)

    assert answer.startswith(b"HTTP/1.1 500")
    assert "Fehler im Webserver bei einer Anfrage: ValueError" in log
    _assert_nothing_from_the_request(log)


def test_normale_anfrage_kommt_gar_nicht_ins_log():
    # Gegenprobe ohne Fehler: Es gibt kein Zugriffsprotokoll.
    raw = b"GET /konto/17/?mail=erika@example.org HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"

    log, answer = _log_of_gunicorn("tests.webserver_apps:ok", raw)

    assert answer.startswith(b"HTTP/1.1 200")
    _assert_nothing_from_the_request(log)
