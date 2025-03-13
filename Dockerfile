# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY mcp_server/requirements.txt mcp_server/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r mcp_server/requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5001

# Set environment variables
ENV FLASK_APP=mcp_server/server.py
ENV QUART_APP=mcp_server/server.py
ENV QUART_ENV=production
ENV PYTHONPATH=/app

# Run the application with hypercorn
CMD ["hypercorn", "mcp_server.server:app", "--bind", "0.0.0.0:5001", "--workers", "1"] 