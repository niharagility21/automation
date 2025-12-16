#!/bin/bash

# Setup script for Real Estate Scraper
# Run this after cloning the repository

echo "======================================"
echo "Real Estate Scraper - Setup"
echo "======================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
playwright install chromium

# Check for Tesseract (optional)
echo ""
if command -v tesseract &> /dev/null; then
    tesseract_version=$(tesseract --version 2>&1 | head -n 1)
    echo "✓ Tesseract found: $tesseract_version"
else
    echo "⚠ Tesseract not found (optional for OCR)"
    echo "  Install with: sudo apt-get install tesseract-ocr"
fi

echo ""
echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "To run the scraper:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: python main.py --site auction"
echo ""
echo "For more info, see README.md"
