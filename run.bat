@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\ui.py %*
) else (
    where uv >nul 2>&1
    if errorlevel 1 (
        echo Falta uv. Consulta la instalacion en README.md.
        pause
        exit /b 1
    )
    uv run --locked --extra ui --extra rl python scripts\ui.py %*
)
if errorlevel 1 (
    echo No se pudo iniciar SAR-Bot. Revisa el mensaje y README.md.
    pause
    exit /b 1
)
endlocal
