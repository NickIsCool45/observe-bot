#!/usr/bin/env bash
# Setup virtual environment and dependencies for Trade Desk

set -e

echo "Setting up Trade Desk..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Copying default configs..."
if [ ! -f "config/rules.local.json" ]; then
    cp config/rules.json config/rules.local.json
    echo "Created config/rules.local.json - edit to customize your watchlist & limits"
fi

if [ ! -f "config/agents.json" ]; then
    cp config/agents.json config/agents.local.json
    echo "Created config/agents.local.json - edit to change OpenRouter models"
fi

echo "Setup complete! Run desk with:"
echo "  source venv/bin/activate"
echo "  python src/runner.py"