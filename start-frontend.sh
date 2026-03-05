#!/bin/bash
# Start the React frontend dev server
set -e

cd "$(dirname "$0")/frontend"

if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "Starting frontend on http://localhost:5173"
npm run dev
