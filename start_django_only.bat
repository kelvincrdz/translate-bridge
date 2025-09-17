@echo off
echo Starting Django server (without frontend build)...

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

echo.
echo Starting Django development server...
echo Access the application at: http://localhost:8000
echo.
echo Note: If frontend is not working, run 'start_integrated.bat' instead
echo to build the frontend first.
echo.

python manage.py runserver

pause
