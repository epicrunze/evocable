#!/bin/bash

# Docker-based test runner for Evocable backend
# This runs tests inside the Docker network to properly access Redis and other services

set -e

echo "🐳 Running tests in Docker environment..."
echo "This ensures tests can access Redis, API, and Storage services properly."

# Build the test image
echo "📦 Building test container..."
docker-compose build test

# Run the tests
echo "🧪 Running test suite..."
docker-compose run --rm test

echo "✅ Docker tests completed!"