# Dockerfile — Clean & Final (the way pros do it)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy only what poetry needs first (perfect layer caching)
COPY pyproject.toml poetry.lock* README.md* ./

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi --no-root

# Copy the actual package code directly into the right place
COPY kalshi_bot/ ./kalshi_bot/

# Install the package in editable mode — this is all you need
RUN pip install -e .

CMD ["python", "-m", "kalshi_bot.core.client"]