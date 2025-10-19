#!/bin/bash
# Build script for frontend and backend

set -e  # Exit on error

echo "🔨 Building Frontend..."
cd frontend
npm install
npm run build
cd ..

echo "✅ Frontend built successfully!"
echo "📦 Static files are in backend/static/"
echo ""
echo "To run the server:"
echo "  cd backend"
echo "  uv run python -m src.main"
