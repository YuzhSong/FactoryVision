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

Push-Location $serviceDir
try {
    & $pythonExe -m unittest discover -s tests -p "test_helmet_detector.py"
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService helmet detector unittest run failed."
    }

    & $pythonExe -m unittest discover -s tests -p "test_face_recognition_service.py"
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService unittest run failed."
    }

    & $pythonExe -m unittest discover -s tests -p "test_liveness_detector.py"
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService liveness unittest run failed."
    }

    & $pythonExe -m unittest discover -s tests -p "test_zone_detector.py"
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService zone detector unittest run failed."
    }

    & $pythonExe -m unittest discover -s tests -p "test_event_report_queue.py"
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService event report queue unittest run failed."
    }

    & $pythonExe -m unittest discover -s tests -p "test_realtime_streaming.py"
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService realtime streaming unittest run failed."
    }
}
finally {
    Pop-Location
}

Write-Host "[FactoryVision] AIService tests passed."
