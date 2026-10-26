@echo off
setlocal

cd /d "%~dp0"

python -m PyInstaller --noconfirm --clean --onefile --windowed --name Open4Terminals open_4_terminals.py
if errorlevel 1 (
    echo.
    echo Build failed. Check that Python and PyInstaller are installed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\Open4Terminals.exe
pause
