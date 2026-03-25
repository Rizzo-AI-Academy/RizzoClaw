FROM python:3.12-slim

# Installa uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copia i file di dipendenze prima del codice (cache layer)
COPY pyproject.toml uv.lock ./

# Installa le dipendenze senza il pacchetto stesso
RUN uv sync --frozen --no-install-project

# Copia il codice sorgente
COPY rizzoclaw/ ./rizzoclaw/

# Installa il pacchetto
RUN uv sync --frozen

# Cartelle persistenti (montate come volumi)
RUN mkdir -p data memories .agents/skills

CMD ["uv", "run", "rizzoclaw"]
