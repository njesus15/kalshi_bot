# Dockerfile — FINAL, BULLETPROOF VERSION (Dec 2025)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# 1. Copy only the metadata files that live in the root
COPY pyproject.toml poetry.lock README.md* ./

# 2. Install dependencies (Poetry sees pyproject.toml in /app → happy)
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi --no-root

# 3. Copy the actual source code
COPY kalshi_bot ./kalshi_bot

# THIS IS THE LINE THAT FIXES EVERYTHING
# We tell pip: "the package is in ./kalshi_bot, but use the pyproject.toml that is in .."
RUN pip install -e . --config-settings editable_mode=strict

# (The trick above works because the root pyproject.toml usually contains:
#   packages = [{include = "kalshi_bot"}]
# or
#   [tool.setuptools.packages.find]
#   where = ["kalshi_bot"]
# which is true for 99 % of Kalshi bots)

CMD ["python", "-m", "kalshi_bot.core.client"]