# Dockerfile — copy-paste exactly
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy only dependency files first (for layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies WITHOUT installing your project as a package
# This avoids the "Readme path does not exist" error
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

# Now copy your actual code
COPY kalshi_bot ./kalshi_bot

# Run the bot
CMD ["python", "-m", "kalshi_bot.core.client"]