@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_kc_zoekmodule.ps1"
echo.
echo Druk op een toets om dit venster te sluiten...
pause >nul
