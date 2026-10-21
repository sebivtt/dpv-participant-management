#!/bin/sh
# Start des Tools im Container (#58): erst die Datenbank auf den neuesten Stand bringen, dann
# den Webserver starten. Bricht etwas ab, etwa weil eine Pflichtangabe fehlt, startet der
# Webserver nicht, und die Meldung steht im Log des Containers. Die Einstellungen des
# Webservers stehen in docker/gunicorn.conf.py.
set -e

python manage.py migrate --noinput
exec gunicorn config.wsgi -c docker/gunicorn.conf.py
