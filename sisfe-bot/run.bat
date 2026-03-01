@echo off
REM ============================================================
REM  Bot SISFE - Lanzador para Windows
REM  Programá este .bat en el Programador de tareas de Windows
REM  para que corra cada 1 hora (o la frecuencia que prefieras).
REM ============================================================

REM Ir al directorio del script (funciona aunque lo llame el Programador de tareas)
cd /d "%~dp0"

REM Activar entorno virtual si existe, sino usar Python del sistema
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Ejecutar el bot y guardar log con timestamp
set LOG_FILE=sisfe_bot.log
echo. >> %LOG_FILE%
echo ===== %DATE% %TIME% ===== >> %LOG_FILE%
python main.py >> %LOG_FILE% 2>&1

REM Mantener solo las últimas 5000 líneas del log para no ocupar disco
powershell -Command "Get-Content %LOG_FILE% -Tail 5000 | Set-Content %LOG_FILE%_tmp; Move-Item %LOG_FILE%_tmp %LOG_FILE% -Force" 2>nul
