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
$serviceDir = Join-Path $repoRoot "ai-service"
$pythonExe = Join-Path $serviceDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Fail "AIService interpreter not found: $pythonExe"
}

$version = & $pythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    Fail "AIService interpreter failed while reading Python version."
}
if (-not $version.StartsWith("3.11")) {
    Fail "AIService must use Python 3.11.x, got $version."
}

Write-Host "[FactoryVision] Starting AIService with $pythonExe"
Write-Host "[FactoryVision] Python version: $version"

Push-Location $serviceDir
try {
    & $pythonExe app.py
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
