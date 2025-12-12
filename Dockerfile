FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy the entire project (now pyproject.toml is inside kalshi_bot/)
COPY . kalshi_bot/

# Install everything from the subfolder
RUN cd kalshi_bot && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi && \
    pip install -e .

CMD ["python", "-m", "kalshi_bot.core.client"]