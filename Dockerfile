# Dockerfile — build and run your bot in one image
FROM python:3.11-slim

# Set work dir
WORKDIR /app

# Copy poetry files + code
COPY pyproject.toml poetry.lock ./
COPY kalshi_bot ./kalshi_bot

# Install deps with poetry
RUN pip install poetry && poetry install --no-dev --no-root

# Run the bot
ENTRYPOINT ["poetry", "run", "python", "kalshi_bot/core/client.py"]