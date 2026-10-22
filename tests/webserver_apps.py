"""Kleine Web-Anwendungen nur für tests/test_webserver_log.py (#58). Im Tool gibt es sie nicht.

Sie laufen ohne Django, damit der Test genau das Verhalten des Webservers gunicorn prüft.
"""


def ok(environ, start_response):
    """Antwortet immer mit „ok“."""
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"ok"]


def failing(environ, start_response):
    """Scheitert mit einem Fehler, dessen Meldungstext Personendaten enthält.

    So scheitert eine Anfrage im Webserver selbst, außerhalb der Fehlerbehandlung von Django.
    Ein Log, das Adresse oder Meldungstext übernimmt, fällt damit sofort auf.
    """
    raise ValueError("geheim: erika.testfrau@example.org")
