@echo off
echo Building frontend and starting Django server...

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Build the frontend
echo.
echo Building React frontend...
python manage.py build_frontend

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Frontend build failed! You may need to:
    echo 1. Install Node.js from https://nodejs.org/
    echo 2. Run 'npm install' in the frontend directory
    echo 3. Or skip the build and run: python manage.py runserver
    echo.
    pause
    exit /b 1
)

echo.
echo Starting Django development server...
python manage.py runserver

pause
