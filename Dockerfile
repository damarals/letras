# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock ./
COPY configs/ ./configs/
COPY core/ ./core/
COPY main.py ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Create data directory
RUN mkdir -p /app/data

# Set entrypoint
ENTRYPOINT ["python", "main.py"]