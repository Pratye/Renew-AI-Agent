# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Configure Poetry
RUN poetry config virtualenvs.create false

# Copy Poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Set environment variables
ENV QUART_APP=mcp_server.server:app
ENV QUART_ENV=production
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5001

# Run the application with Hypercorn
CMD ["poetry", "run", "hypercorn", "--bind", "0.0.0.0:5001", "mcp_server.server:app"] 