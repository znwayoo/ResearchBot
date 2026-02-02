# Build ResearchBot as a Windows desktop app (run on Windows with venv active).
# Requires: pip install pyinstaller

Set-Location $PSScriptRoot

Write-Host "Building ResearchBot.exe..."
pyinstaller ResearchBot-windows.spec

Write-Host ""
Write-Host "App built: dist\ResearchBot\ResearchBot.exe"
Write-Host "Run: .\dist\ResearchBot\ResearchBot.exe"
