#!/bin/bash

# Kalshi Weather Trading Bot - Deployment Script

# Exit on any error
set -e

echo "Deploying Kalshi Weather Trading Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p data models backtests logs

# Copy example env file if .env doesn't exist
echo "Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Please update .env with your API credentials before running the bot."
fi

echo "Deployment completed successfully!"
echo "To run the bot:"
echo "  source venv/bin/activate"
echo "  python main.py --help"
