param(
    [int]$Port = 5175
)

$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

$repoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
$frontendDir = Join-Path $repoRoot "frontend"
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue

if ($null -eq $npm) {
    Fail "npm.cmd was not found. Install a supported Node.js runtime before starting the frontend."
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
    Fail "Frontend dependencies are missing. Run 'npm.cmd install' once in $frontendDir."
}

Write-Host "[FactoryVision] Starting frontend at http://127.0.0.1:$Port"
Push-Location $frontendDir
try {
    & $npm.Source run dev -- --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) {
        Fail "Frontend exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
