# Smoke-check a running Cursus stack (local or VPS).
# Usage:
#   pwsh scripts/deploy_smoke.ps1
#   pwsh scripts/deploy_smoke.ps1 -ApiBase http://127.0.0.1:8000 -WebBase http://127.0.0.1:3000

param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$WebBase = "http://127.0.0.1:3000",
    [string]$Email = "",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

function Assert-Ok([string]$Name, [scriptblock]$Block) {
    try {
        & $Block
        Write-Host "OK  $Name" -ForegroundColor Green
    }
    catch {
        Write-Host "FAIL $Name - $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

Assert-Ok "backend /health" {
    $r = Invoke-RestMethod -Uri "$ApiBase/health" -Method GET -TimeoutSec 10
    if ($r.status -ne "ok") { throw "unexpected health payload" }
}

Assert-Ok "frontend root" {
    $r = Invoke-WebRequest -Uri "$WebBase/" -Method GET -TimeoutSec 10 -UseBasicParsing
    if ($r.StatusCode -ne 200) { throw "status $($r.StatusCode)" }
}

if ($Email -and $Password) {
    Assert-Ok "auth login" {
        $body = @{ email = $Email; password = $Password; remember_me = $true } | ConvertTo-Json
        $r = Invoke-RestMethod -Uri "$ApiBase/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 20
        if (-not $r.user) { throw "missing user in login response" }
    }
}
else {
    Write-Host "SKIP auth login (pass -Email / -Password to enable)" -ForegroundColor Yellow
}

Write-Host "`nSmoke checks passed." -ForegroundColor Green
