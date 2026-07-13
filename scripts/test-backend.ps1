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

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Fail "Backend interpreter not found: $pythonExe"
}

Push-Location $backendDir
try {
    & $pythonExe manage.py check
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend manage.py check failed."
    }

    & $pythonExe manage.py test apps.employees apps.face
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend employee and face tests failed."
    }
}
finally {
    Pop-Location
}

Write-Host "[FactoryVision] Backend checks passed."
