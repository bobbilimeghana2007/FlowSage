# Starts API (port 8000) and UI (port 5173). Loads .env; generates a random secret if none is set.
$ErrorActionPreference = "Stop"
Get-Content .env | Where-Object { $_ -match '^\s*[A-Z_]+=' } | ForEach-Object {
  $k, $v = ($_ -split '#')[0] -split '=', 2; $v = $v.Trim()
  if ($v) { [Environment]::SetEnvironmentVariable($k.Trim(), $v, "Process") } }
if (-not $env:FLOWSAGE_SECRET_KEY) {
  $env:FLOWSAGE_SECRET_KEY = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]]) }
Start-Process powershell -ArgumentList "-NoExit","-Command","cd backend; .\.venv\Scripts\python -m uvicorn flowsage.api:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd frontend; npm run dev"
Write-Host "Open http://localhost:5173"
