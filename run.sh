#!/bin/bash

# Solana Bonding Curve Monitor Bot Runner
# This script starts the Telegram bot

echo "🎯 Starting Solana Bonding Curve Monitor Bot..."
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and add your API keys:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if requirements are installed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing/updating dependencies..."
pip install -r requirements.txt

echo "🚀 Starting bot..."
python main.py