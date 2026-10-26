@echo off
setlocal

set "SCRIPT=%~dp0open_4_terminals.py"

where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%SCRIPT%"
    exit /b %errorlevel%
)

python.exe "%SCRIPT%"
