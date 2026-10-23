$ErrorActionPreference = "Stop"
Push-Location backend
..\backend\.venv\Scripts\python -m unittest discover -s tests -v
Pop-Location
