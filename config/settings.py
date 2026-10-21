"""Einstellungen des DPV Anmeldetools.

Zugangsdaten und alles, was sich je Rechner unterscheidet, kommen aus Umgebungsvariablen
(NFA-10). Lokal stehen sie in der Datei .env, die nie ins Repo kommt; die Vorlage ist
.env.example. Fehlt eine Pflichtangabe, bricht der Start mit einer verständlichen
Meldung ab, statt mit einem unsicheren Ersatzwert weiterzulaufen.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def required_env(name: str) -> str:
    """Liest eine Pflichtangabe aus der Umgebung; fehlt sie oder ist sie leer, bricht der Start ab."""
    value = os.environ.get(name, "")
    if not value:
        raise ImproperlyConfigured(
            f"Die Umgebungsvariable {name} fehlt. Lokal: .env.example nach .env kopieren (README.md)."
        )
    return value


SECRET_KEY = required_env("DJANGO_SECRET_KEY")

# Gerüst für #58; die Umsetzung folgt.
TEST_ENVIRONMENT = False

# Die Fehleranzeige für Entwickler zeigt Formularinhalte und Einstellungen. Sie ist
# deshalb nur an, wenn sie ausdrücklich eingeschaltet wird, nie als Standard.
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "core",
    "accounts",
]

MIDDLEWARE = [
    # Ganz außen, damit sie auch „kein Zugriff“ aus den übrigen Bausteinen sieht (#6).
    "core.errors.ClientErrorLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Liefert Gestaltung und Skripte vom eigenen Server (#7, CONTRIBUTING.md, Abschnitt 6),
    # auch ohne Fehleranzeige für Entwickler und vor der Login-Pflicht: Die Login-Seite
    # braucht sie schon, bevor jemand angemeldet ist.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Jede Adresse verlangt einen Login, außer sie ist ausdrücklich als öffentlich markiert
    # (CONTRIBUTING.md, Abschnitt 4). Was jemand vergisst zu schützen, ist so trotzdem geschützt.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.navigation.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Nur PostgreSQL, auch in den Tests: So prüfen die Tests dieselbe Datenbank, die
# später im Betrieb läuft.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("POSTGRES_DB"),
        "USER": required_env("POSTGRES_USER"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Oberfläche nur auf Deutsch, Texte aber übersetzbar (NFA-02).
LANGUAGE_CODE = "de"
LANGUAGES = [("de", "Deutsch")]
USE_I18N = True
TIME_ZONE = "Europe/Berlin"
USE_TZ = True

STATIC_URL = "static/"
# WhiteNoise liest die Dateien direkt aus den Ordnern static/ der Apps. Ein eigener Schritt
# zum Einsammeln (collectstatic, braucht STATIC_ROOT) ist so weder lokal noch in der Prüfung
# nötig; für den Betrieb wird das in P6 neu bewertet.
WHITENOISE_USE_FINDERS = True

# Fußbereich jeder Seite (#7). Die Ziele zeigen vorerst auf die Seiten des DPV; ob die
# reichen, klärt Sebastian mit der Datenschutzperson (OP-2, #12).
IMPRESSUM_URL = os.environ.get("IMPRESSUM_URL", "https://dpvonline.de/impressum/")
DATENSCHUTZ_URL = os.environ.get("DATENSCHUTZ_URL", "https://dpvonline.de/datenschutz/")
COPYRIGHT_HOLDER = os.environ.get("COPYRIGHT_HOLDER", "DPV e.V.")
# Ab diesem Jahr zählt der Copyright-Hinweis, z. B. „2026–2027“.
COPYRIGHT_START_YEAR = 2026

# Login nur über den Keycloak des DPV (#5, ORG-02). Das Tool nutzt einen normalen
# Login-Client und schreibt nichts nach Keycloak.
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["allauth.account.auth_backends.AuthenticationBackend"]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "start"

# Adresse des Realms, z. B. http://localhost:8080/realms/dpv, und Zugang des Login-Clients.
# Fehlen sie, meldet die Systemprüfung beim Start einen Fehler (accounts/checks.py). Sie
# sind hier nicht Pflicht, damit sich die übrigen Einstellungen auch ohne sie laden lassen.
KEYCLOAK_REALM_URL = os.environ.get("KEYCLOAK_REALM_URL", "").rstrip("/")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")

# Schalter für den Link „Noch kein Konto? Registrieren“ (0 = ausgeblendet) und die Adresse,
# die die Login-Seite stattdessen nennt.
REGISTRATION_LINK_ENABLED = os.environ.get("REGISTRATION_LINK_ENABLED", "1") != "0"
ACCOUNT_HELP_EMAIL = os.environ.get("ACCOUNT_HELP_EMAIL", "anmeldetool@dpvonline.de")

# Nach so vielen Minuten ohne Aktivität endet die Sitzung (#5). Jede Anfrage verlängert sie.
SESSION_IDLE_MINUTES = 120
SESSION_COOKIE_AGE = SESSION_IDLE_MINUTES * 60
SESSION_SAVE_EVERY_REQUEST = True

# allauth: nur der Login über Keycloak, keine eigene Anmeldung mit Passwort und keine
# eigene Registrierung. Konten werden nie über die Mail gefunden oder verknüpft; zwei
# Konten mit derselben Mail sind deshalb möglich (Entscheidung zu #5, Umgang damit in #8).
SOCIALACCOUNT_ONLY = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = False
ACCOUNT_ADAPTER = "accounts.adapter.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.SocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
# Der Login startet nur mit einem Formular (POST), nie über einen bloßen Link.
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "OAUTH_PKCE_ENABLED": True,
        "APPS": [
            {
                "provider_id": "keycloak",
                "name": "DPV-Konto",
                "client_id": KEYCLOAK_CLIENT_ID,
                "secret": KEYCLOAK_CLIENT_SECRET,
                "settings": {"server_url": KEYCLOAK_REALM_URL, "fetch_userinfo": True},
            }
        ],
    }
}

# Fehlerprotokoll ohne Personendaten (DSG-08, #6). Alles geht in die Ausgabe des Servers;
# wo und wie lange es aufbewahrt wird, klärt #11 (P6). Ersetzt Djangos Grundeinstellung
# vollständig, auch deren Fehlerbericht per Mail.
ADMINS = []
MANAGERS = []
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # Zeigt bei Fehlern nur Art und Stellen im Code, nie den Meldungstext (core/errors.py).
        "safe": {
            "()": "core.errors.SafeFormatter",
            "format": "{asctime} {levelname} {name} {message}",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "safe"},
        # Schreibt nichts. Ein Logger ganz ohne Ausgabe, der nichts weitergibt, landet sonst in
        # Pythons Notausgabe, und die schreibt alles ab „Warnung“ doch ins Log (#25).
        "nichts": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Djangos eigene Zeilen zu Fehlern, „nicht gefunden“ und „kein Zugriff“ enthalten die
        # echte Adresse. Sie sind abgeschaltet; core.errors schreibt stattdessen eigene Zeilen.
        "django.request": {"handlers": ["nichts"], "propagate": False},
        # Ebenso Djangos Zeilen zu verdächtigen Anfragen und zum Formularschutz (CSRF): Sie
        # enthalten die echte Adresse oder frei gewählten Text, z. B. aus dem Namen des Servers.
        "django.security": {"handlers": ["nichts"], "propagate": False},
        # Der Testserver auf dem eigenen Rechner (runserver) zeigt Adressen mit Parametern.
        # Er läuft nur lokal mit erfundenen Daten; der Webserver im Betrieb kommt mit #11.
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "core": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "accounts": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
