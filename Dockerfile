# Use an official Python runtime as the base image
FROM python:3.8-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.4.0 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/var/cache/pypoetry

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    git \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry \
    && apt-get purge -y --auto-remove curl gcc git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Copy the application code before installing dependencies
COPY automation/ automation/
COPY utils/ utils/
COPY monitoring/ monitoring/
COPY prediction/ prediction/

# Copy other files we need
COPY scripts/ scripts/
COPY config.yaml .
COPY data/ data/
COPY README.md .

# Copy the main entry point
COPY main.py .

# Install project dependencies using the updated Poetry command
RUN poetry install --no-dev --no-interaction --no-ansi

# Create necessary directories for logs and data
RUN mkdir -p data logs

# Set environment variables for Fly.io (modify as needed)
ENV FLY_APP_NAME=your-fly-app-name

# Expose ports if your application uses any (modify if necessary)
# EXPOSE 8000

# Define the default command to run your application
CMD ["python", "main.py"]
