$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$DevCompose = Join-Path $Root "docker\docker-compose.dev.yml"
$ProdCompose = Join-Path $Root "docker\docker-compose.prod.yml"

function Write-Info($msg) { Write-Host "[Docker] $msg" -ForegroundColor Cyan }

Write-Info "Building all Docker services..."
docker compose -f $ComposeFile build --no-cache
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Info "Build completed successfully."
