"""Ein Programm, das bei localhost mit Keycloak spricht wie ein Browser (#5, #58).

Ohne Django, damit es auch die Prüfung der Testumgebung im Container (containertests/) nutzen kann.
"""

import requests


class BrowserOnLocalhost(requests.Session):
    """Schickt Keycloak seine Cookies zurück, wie ein Browser es bei localhost tut.

    Keycloak markiert seine Cookies als „nur über HTTPS“. Browser schicken sie bei localhost
    trotzdem mit, requests nicht; ohne das meldet Keycloak „cookie_not_found“.
    """

    def prepare_request(self, request):
        for cookie in self.cookies:
            cookie.secure = False
        return super().prepare_request(request)
