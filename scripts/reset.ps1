$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$DevCompose = Join-Path $Root "docker\docker-compose.dev.yml"

$Confirm = Read-Host "This will remove all volumes and recreate containers. Continue? (y/N)"
if ($Confirm -ne "y") { Write-Host "Aborted."; exit 0 }

Write-Host "[Docker] Resetting environment..." -ForegroundColor Cyan
docker compose -f $ComposeFile -f $DevCompose down -v
docker system prune -f
Write-Host "[Docker] Reset complete. Run .\scripts\start.ps1 to restart." -ForegroundColor Green
