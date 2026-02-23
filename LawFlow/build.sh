#!/bin/bash
set -e

echo "=== Installing Python dependencies ==="
pip install -q -r requirements.txt

echo "=== Building frontend ==="
cd frontend && npm install && npm run build && cd ..

echo "=== Build complete — frontend/dist/ ready ==="
