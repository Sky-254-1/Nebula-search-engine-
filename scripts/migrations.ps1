$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$DevCompose = Join-Path $Root "docker\docker-compose.dev.yml"

Write-Host "[Docker] Running database migrations..." -ForegroundColor Cyan
docker compose -f $ComposeFile -f $DevCompose exec -T backend python -m app.database.migrate
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "[Docker] Migrations applied successfully." -ForegroundColor Green
