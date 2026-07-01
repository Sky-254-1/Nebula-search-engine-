$ErrorActionPreference = "Stop"
$Script:Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "docker\docker-compose.yml"
$ProdCompose = Join-Path $Root "docker\docker-compose.prod.yml"

if (-not $Args[0]) {
    Write-Host "Usage: .\restore.ps1 <backup-file.sql.gz>" -ForegroundColor Red
    exit 1
}

$InputFile = $Args[0]
if (-not (Test-Path $InputFile)) {
    Write-Host "Backup file not found: $InputFile" -ForegroundColor Red
    exit 1
}

Write-Host "[Docker] Restoring PostgreSQL from $InputFile..." -ForegroundColor Cyan
$InputContent = Get-Content $InputFile -Raw
$InputContent | docker compose -f $ComposeFile -f $ProdCompose exec -T postgres psql -U nebula nebula
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "[Docker] Restore completed successfully." -ForegroundColor Green
