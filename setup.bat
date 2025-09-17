@echo off
REM EPUB Translator - Windows Development Setup Script

echo 🚀 EPUB Translator Setup Script
echo ================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
set REQUIRED_VERSION=3.8

REM Simple version check (this is basic, you might want to improve it)
echo ✅ Python detected

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate

REM Upgrade pip
echo ⬆️  Upgrading pip...
pip install --upgrade pip

REM Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo 📝 Creating .env file...
    copy .env.example .env
    echo ⚠️  Please edit .env file with your configuration before running the server.
)

REM Run migrations
echo 🗄️  Running database migrations...
python manage.py migrate

REM Create superuser (optional)
set /p CREATE_USER="👤 Do you want to create a superuser? (y/n): "
if /i "%CREATE_USER%"=="y" (
    python manage.py createsuperuser
)

REM Check if Redis is running
redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis is running
) else (
    echo ⚠️  Redis is not running. Please start Redis:
    echo    redis-server
)

echo.
echo 🎉 Setup complete!
echo.
echo To start the development server:
echo 1. Start Redis (if using Celery): redis-server
echo 2. Start Celery worker: celery -A epub_api worker -l info
echo 3. Start Django server: python manage.py runserver
echo.
echo Or use Docker:
echo docker-compose up --build
echo.
echo API will be available at: http://localhost:8000
echo API documentation: http://localhost:8000/api/docs/

pause
