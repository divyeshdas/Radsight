#!/bin/bash
set -e

echo "Setting up RadSight..."

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env created from .env.example — update secrets before running"
fi

mkdir -p uploads faiss_index logs

if command -v docker &> /dev/null; then
  echo "Starting infrastructure services..."
  docker compose up -d mongodb redis
  echo "Waiting for MongoDB and Redis to be healthy..."
  sleep 8
fi

echo "RadSight setup complete."
echo "Run: docker compose up --build"
