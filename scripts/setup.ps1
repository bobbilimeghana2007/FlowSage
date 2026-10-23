# Run from the project root in PowerShell:  .\scripts\setup.ps1
$ErrorActionPreference = "Stop"
Write-Host "Checking tools..."; python --version; node --version; npm --version; git --version
Get-PSDrive C | ForEach-Object { "Free disk on C: {0:N1} GB" -f ($_.Free/1GB) }
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env (demo-safe defaults)" }
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install --upgrade pip
backend\.venv\Scripts\pip install -r backend\requirements.txt
Push-Location frontend; npm install; Pop-Location
Write-Host "Setup complete. Run tests: .\scripts\test.ps1   Start app: .\scripts\start.ps1"
