#!/bin/sh
# Start des Tools im Container (#58): erst die Datenbank auf den neuesten Stand bringen, dann
# den Webserver starten. Bricht etwas ab, etwa weil eine Pflichtangabe fehlt, startet der
# Webserver nicht, und die Meldung steht im Log des Containers.
#
# Der Webserver gunicorn schreibt bewusst kein Zugriffsprotokoll: Es enthielte jede echte
# Adresse mit Nummern und Parametern (Entscheidung zu #6). Ob und wie es im Betrieb eins
# braucht, klärt #11. Ebenso ohne Steuerzugang (control socket), der nicht gebraucht wird.
set -e

python manage.py migrate --noinput
exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2 --no-control-socket
