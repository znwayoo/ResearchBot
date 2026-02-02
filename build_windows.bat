@echo off
REM Build ResearchBot as a Windows desktop app (run on Windows with venv active).
REM Requires: pip install pyinstaller

cd /d "%~dp0"

echo Building ResearchBot.exe...
pyinstaller ResearchBot-windows.spec

echo.
echo App built: dist\ResearchBot\ResearchBot.exe
echo Run: dist\ResearchBot\ResearchBot.exe
pause
