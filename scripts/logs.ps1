$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$DevCompose = Join-Path $Root "docker\docker-compose.dev.yml"
$Service = if ($Args[0]) { $Args[0] } else { "" }

Write-Host "[Docker] Showing logs (tail 200)..." -ForegroundColor Cyan
if ($Service) {
    docker compose -f $ComposeFile -f $DevCompose logs --tail 200 $Service
} else {
    docker compose -f $ComposeFile -f $DevCompose logs --tail 200
}
