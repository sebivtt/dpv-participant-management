#!/bin/sh
# Dienst „aufraeumen“ der Testumgebung (#324): löscht abgelaufene Sitzungen aus der Datenbank,
# beim Start sofort und danach etwas öfter als alle 24 Stunden (der Lauf selbst braucht Zeit).
# Gültige Sitzungen bleiben; wer angemeldet ist, bleibt es. Scheitert ein Lauf, etwa weil die
# Datenbank nach einem Neustart des Servers noch nicht bereit ist, steht die Meldung im Log des
# Dienstes, und nach einer Minute kommt der nächste Versuch.

while true; do
    if python manage.py clearsessions; then
        sleep 86000
    else
        sleep 60
    fi
done
