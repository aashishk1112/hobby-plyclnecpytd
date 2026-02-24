#!/bin/bash
set -e

echo "🛠️ Building Scalar Planck locally with Docker..."

# Build Backend
echo "📦 Building Backend..."
docker build -t scalar-backend:local ./backend

# Build Frontend
echo "📦 Building Frontend..."
docker build -t scalar-frontend:local ./frontend

echo "✅ Local build complete! Run with: docker-compose up"
