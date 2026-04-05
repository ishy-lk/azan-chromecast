#!/bin/bash

# Prayer Times Chromecast Setup Script
# This script sets up the environment for the Azan Chromecast system

set -e  # Exit on error

echo "🕌 Prayer Times Chromecast Setup"
echo "================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $(python3 --version)"

# Ask if user wants to use virtual environment
echo ""
read -p "Create a virtual environment? (recommended) [Y/n]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"

    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Install requirements
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Configuration reminder
echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Update prayer_times.py with your configuration:"
echo "   - SPEAKER_OR_GROUP_NAME: Your Chromecast device name(s)"
echo "   - LAT/LON: Your location coordinates"
echo "   - LOCATION: Your city name"
echo ""
echo "2. Add your audio files:"
echo "   - fajr_azan.mp3 (for Fajr prayer)"
echo "   - standard_azan.mp3 (for other prayers)"
echo ""
echo "3. Test the setup:"
echo "   python3 prayer_times.py --test"
echo ""
echo "4. Run the scheduler:"
echo "   python3 prayer_times.py"
echo ""
echo "Note: If you created a virtual environment, activate it before running:"
echo "   source venv/bin/activate"
