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
    "core",
]

MIDDLEWARE = [
    # Ganz außen, damit sie auch „kein Zugriff“ aus den übrigen Bausteinen sieht (#6).
    "core.errors.ClientErrorLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Djangos eigene Zeilen zu Fehlern, „nicht gefunden“ und „kein Zugriff“ enthalten die
        # echte Adresse. Sie sind abgeschaltet; core.errors schreibt stattdessen eigene Zeilen.
        "django.request": {"handlers": [], "propagate": False},
        # Der Testserver auf dem eigenen Rechner (runserver) zeigt Adressen mit Parametern.
        # Er läuft nur lokal mit erfundenen Daten; der Webserver im Betrieb kommt mit #11.
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "core": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
