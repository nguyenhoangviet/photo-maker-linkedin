#!/bin/bash
# Start the FastAPI backend
set -e

cd "$(dirname "$0")/backend"

# Create virtualenv if needed
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies (first run installs torch + diffusers — may take a few minutes)..."
pip install -q -r requirements.txt

echo ""
echo "NOTE: First time you enable 'Change Outfit with Local AI', the Stable Diffusion"
echo "      inpainting model (~3.4GB) will download from HuggingFace and cache locally."
echo "      All subsequent runs use the cached model — no internet required."
echo ""
echo "Starting backend on http://localhost:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
