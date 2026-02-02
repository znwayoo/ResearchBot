#!/usr/bin/env bash
# Build ResearchBot as a Mac desktop .app (run on macOS with venv active).
# Requires: pip install pyinstaller

set -e
cd "$(dirname "$0")"

echo "Building ResearchBot.app..."
pyinstaller ResearchBot.spec

echo ""
echo "App built: dist/ResearchBot.app"
echo "Run: open dist/ResearchBot.app"
