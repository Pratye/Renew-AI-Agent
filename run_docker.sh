#!/bin/bash

# Stop any running containers
echo "Stopping any running containers..."
docker-compose down

# Build and start the containers
echo "Building and starting the containers..."
docker-compose up --build -d

# Show the logs
echo "Showing logs (press Ctrl+C to exit)..."
docker-compose logs -f 