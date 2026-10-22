"""Einstellungen des Webservers gunicorn im Container (#58), gelesen von docker/start.sh.

Kein Zugriffsprotokoll (accesslog bleibt aus): Es enthielte jede echte Adresse mit Nummern und
Parametern (Entscheidung zu #6); ob und wie der Betrieb eins braucht, klärt #11. Das übrige
Log von gunicorn läuft über core.gunicorn_log.SafeLogger, ohne Daten aus der Anfrage. Kein
Steuerzugang (control socket): gunicorn legte ihn sonst im Benutzerordner an, gebraucht wird
er nicht, und der Benutzer im Abbild hat absichtlich keinen eigenen Ordner.
"""

bind = "0.0.0.0:8000"
workers = 2
logger_class = "core.gunicorn_log.SafeLogger"
loglevel = "info"
control_socket_disable = True
