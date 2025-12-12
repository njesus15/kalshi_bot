# Dockerfile — FINAL VERSION THAT ACTUALLY WORKS (copy-paste this)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create /app and set as workdir
RUN mkdir -p /app && chmod 755 /app
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# 1. Copy ONLY the files Poetry needs to resolve dependencies
#    (this layer can be cached forever if pyproject.toml doesn't change)
COPY pyproject.toml poetry.lock README.md* ./

# 2. Install dependencies (Poetry now sees pyproject.toml in /app → happy)
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi --no-root

# 3. Copy the actual source code into the kalshi_bot directory
#    (this creates /app/kalshi_bot/ exactly like your local folder)
RUN mkdir -p kalshi_bot
COPY kalshi_bot/ kalshi_bot/

# 4. Install the package in editable mode from the root (/app)
#    This makes `from kalshi_bot.core...` work perfectly
RUN pip install -e .

# Optional: show what got installed (helpful for debugging)
# RUN pip list

# Run the bot
CMD ["python", "-m", "kalshi_bot.core.client"]