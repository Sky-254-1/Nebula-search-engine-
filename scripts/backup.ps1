$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$ProdCompose = Join-Path $Root "docker\docker-compose.prod.yml"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Output = Join-Path $Root "database\backups\nebula_$Timestamp.sql.gz"

Write-Host "[Docker] Creating PostgreSQL backup..." -ForegroundColor Cyan
docker compose -f $ComposeFile -f $ProdCompose exec -T postgres pg_dump -U nebula nebula | gzip > $Output
if ($LASTEXITCODE -ne 0) { Remove-Item $Output -ErrorAction SilentlyContinue; exit 1 }
Write-Host "[Docker] Backup saved to $Output" -ForegroundColor Green
