@echo off
cd /d "%~dp0"

echo Iniciando Celery Worker...
echo Certifique-se de que o Redis esteja rodando!

.\.venv\Scripts\celery.exe -A epub_api worker --loglevel=info --pool=solo

pause
