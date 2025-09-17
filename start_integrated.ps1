#!/usr/bin/env pwsh

Write-Host "Building frontend and starting Django server..." -ForegroundColor Green

# Build the frontend
Write-Host ""
Write-Host "Building React frontend..." -ForegroundColor Yellow
python manage.py build_frontend

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Starting Django development server..." -ForegroundColor Yellow
python manage.py runserver
