$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$DevCompose = Join-Path $Root "docker\docker-compose.dev.yml"

Write-Host "[Docker] Stopping all services..." -ForegroundColor Cyan
docker compose -f $ComposeFile -f $DevCompose down
if ($LASTEXITCODE -ne 0) { docker compose -f $ComposeFile down }
Write-Host "[Docker] Services stopped." -ForegroundColor Green
