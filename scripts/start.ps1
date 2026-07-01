$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$DevCompose = Join-Path $Root "docker\docker-compose.dev.yml"
$EnvFile = Join-Path $Root "backend\.env"
$Mode = if ($Args[0] -eq "prod") { "production" } else { "development" }

if ($Mode -eq "development") {
    Write-Host "[Docker] Starting in DEVELOPMENT mode..." -ForegroundColor Cyan
    if (-not (Test-Path $EnvFile)) {
        Write-Warning "backend\.env not found. Copying from backend\.env.example..."
        Copy-Item (Join-Path $Root "backend\.env.example") $EnvFile
    }
    docker compose -f $ComposeFile -f $DevCompose up -d --build
} else {
    Write-Host "[Docker] Starting in PRODUCTION mode..." -ForegroundColor Cyan
    if (-not (Test-Path $EnvFile)) {
        Write-Host "backend\.env not found. Exiting." -ForegroundColor Red
        exit 1
    }
    docker compose -f $ComposeFile -f $ProdCompose up -d
}

if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "[Docker] Services started. Run .\scripts\logs.ps1 to see output." -ForegroundColor Green
