$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$ProdCompose = Join-Path $Root "docker-compose.prod.yml"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Output = Join-Path $Root "database\backups\nebula_$Timestamp.sql"

if (-not (Test-Path (Split-Path $Output -Parent))) {
    New-Item -ItemType Directory -Path (Split-Path $Output -Parent) -Force | Out-Null
}

Write-Host "[Docker] Creating PostgreSQL backup..." -ForegroundColor Cyan
docker compose -f $ComposeFile -f $ProdCompose exec -T postgres pg_dump -U nebula nebula > $Output
if ($LASTEXITCODE -ne 0) { Remove-Item $Output -ErrorAction SilentlyContinue; exit 1 }
Write-Host "[Docker] Backup saved to $Output" -ForegroundColor Green
