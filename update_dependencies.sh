#!/bin/bash

# Update dependencies
echo "Updating dependencies..."
poetry update

# Install new dependencies
echo "Installing new dependencies..."
poetry install

echo "Dependencies updated successfully!" 