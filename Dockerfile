# Dockerfile — FINAL VERSION (copy-paste exactly)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ←←← CRITICAL FIX FOR BUILDX / GITHUB ACTIONS ←←←
# Create /app as a directory FIRST, before any COPY that might conflict
RUN mkdir -p /app && chmod 755 /app
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files
COPY pyproject.toml poetry.lock README.md* ./

# Install dependencies (no virtualenv, no root install)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy your code
COPY kalshi_bot ./kalshi_bot

# ←←← THIS LINE FIXES ALL IMPORTS ←←←
# Install the package in editable mode so `from kalshi_bot...` works
RUN pip install -e .

# Run the bot
CMD ["python", "-m", "kalshi_bot.core.client"]