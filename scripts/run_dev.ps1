$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Update DATABASE_URL if needed."
}

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

