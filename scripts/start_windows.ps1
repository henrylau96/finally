# Build (if needed) and run the FinAlly container. Usage: start_windows.ps1 [-Build] [-NoBrowser]
param([switch]$Build, [switch]$NoBrowser)

Set-Location (Join-Path $PSScriptRoot "..")
$Image = "finally"
$Container = "finally"
$Url = "http://localhost:8000"

if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env not found, creating it from .env.example. Add your OPENROUTER_API_KEY."
    Copy-Item ".env.example" ".env"
}

docker image inspect $Image *> $null
if ($Build -or $LASTEXITCODE -ne 0) {
    docker build -t $Image .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

docker rm -f $Container *> $null
docker run -d --name $Container -v finally-data:/app/db -p 8000:8000 --env-file .env $Image | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "FinAlly is running at $Url"
if (-not $NoBrowser) { Start-Process $Url }
