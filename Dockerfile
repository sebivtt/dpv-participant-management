# Bauvorlage des Container-Abbilds (#58): das Tool mit einem Webserver für den Betrieb.
# Gebaut wird es aus dem Repo: lokal (testumgebung/docker-compose.yml) und auf GitHub für den Server
# (.github/workflows/abbild-veroeffentlichen.yml, #302); der Server holt das fertige Abbild.
# Das Abbild enthält keine Zugangsdaten; die kommen beim Start aus der Umgebungsdatei.

# Grundabbilder mit fester Fassung und Prüfsumme, damit jeder Bau dieselbe Grundlage hat (#324);
# aktualisiert wird nur per Pull Request (docs/betrieb.md).
# uv in derselben Fassung wie in der Prüfung auf GitHub (.github/workflows/ci.yml).
FROM ghcr.io/astral-sh/uv:0.13.4@sha256:9f130421e930bfbdc563c00740466603f8723158e90297d07957c2294640262b AS uv

FROM python:3.13.18-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

COPY --from=uv /uv /usr/local/bin/uv

# Pakete fest aus uv.lock, ohne die Pakete nur zum Prüfen. Python bringt das Abbild mit;
# uv lädt keins nach.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Erst nur die Paketlisten: Ändert sich nur der Code, muss Docker die Pakete nicht neu holen.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

# Das Tool läuft nicht als Verwalter des Containers. Es braucht nur Lesezugriff auf seine Dateien.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin tool
USER tool

EXPOSE 8000
CMD ["sh", "docker/start.sh"]
