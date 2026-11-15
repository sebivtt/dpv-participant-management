#!/bin/sh
# Dienst „aufraeumen“ der Testumgebung (#324): löscht abgelaufene Sitzungen aus der Datenbank,
# beim Start sofort und danach alle 24 Stunden. Gültige Sitzungen bleiben; wer angemeldet ist,
# bleibt es. Scheitert ein Lauf, steht die Meldung im Log des Dienstes, und der nächste Lauf
# kommt trotzdem.

while true; do
    python manage.py clearsessions
    sleep 86400
done
