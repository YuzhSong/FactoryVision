$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)

    Write-Error $Message
    exit 1
}

function Get-RepoRoot {
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

$repoRoot = Get-RepoRoot
$backendDir = Join-Path $repoRoot "backend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"
$localAiToken = "factoryvision-local-e2e-token"

if (-not $env:AI_SERVICE_API_TOKEN) {
    $env:AI_SERVICE_API_TOKEN = $localAiToken
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Fail "Backend interpreter not found: $pythonExe"
}

Write-Host "[FactoryVision] Checking backend environment with $pythonExe"

Push-Location $backendDir
try {
    & $pythonExe --version
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend interpreter failed to start."
    }

    & $pythonExe -m pip check
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend pip check failed."
    }

    & $pythonExe manage.py check
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend manage.py check failed."
    }

    Write-Host "[FactoryVision] Starting Backend ASGI server on 127.0.0.1:8000"
    & $pythonExe -m daphne -b 127.0.0.1 -p 8000 config.asgi:application
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
