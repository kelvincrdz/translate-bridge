#!/bin/bash
# EPUB Translator - Development Setup Script

set -e

echo "🚀 EPUB Translator Setup Script"
echo "================================"

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION is not supported. Please use Python $REQUIRED_VERSION or higher."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows (uncomment if on Windows)

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before running the server."
fi

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate

# Create superuser (optional)
read -p "👤 Do you want to create a superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

# Check if Redis is running
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis is not running. Please start Redis:"
        echo "   redis-server"
    fi
else
    echo "⚠️  Redis is not installed. Please install Redis for Celery support."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the development server:"
echo "1. Start Redis (if using Celery): redis-server"
echo "2. Start Celery worker: celery -A epub_api worker -l info"
echo "3. Start Django server: python manage.py runserver"
echo ""
echo "Or use Docker:"
echo "docker-compose up --build"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/api/docs/"
