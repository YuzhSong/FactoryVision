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

function Assert-CommandSuccess {
    param(
        [string]$Description,
        [scriptblock]$Action
    )

    Write-Host "==> $Description"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Fail "$Description failed with exit code $LASTEXITCODE."
    }
}

function Assert-FileExists {
    param(
        [string]$Path,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        Fail "$Description not found: $Path"
    }
}

function Assert-PythonVersionPrefix {
    param(
        [string]$PythonExe,
        [string]$ExpectedPrefix,
        [string]$ServiceName
    )

    $version = & $PythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
    if ($LASTEXITCODE -ne 0) {
        Fail "$ServiceName interpreter failed while reading Python version."
    }

    Write-Host "$ServiceName Python version: $version"
    if (-not $version.StartsWith($ExpectedPrefix)) {
        Fail "$ServiceName must use Python $ExpectedPrefix.x, got $version."
    }
}

function Run-ImportCheck {
    param(
        [string]$PythonExe,
        [string]$ModuleName
    )

    Assert-CommandSuccess "Import $ModuleName" {
        & $PythonExe -c "import $ModuleName; print('$ModuleName ok')"
    }
}

$repoRoot = Get-RepoRoot
$aiServiceDir = Join-Path $repoRoot "ai-service"
$backendDir = Join-Path $repoRoot "backend"
$aiPython = Join-Path $aiServiceDir ".venv\Scripts\python.exe"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"

Write-Host "[FactoryVision] Repository root: $repoRoot"

Write-Host ""
Write-Host "[AIService]"
Assert-FileExists -Path $aiPython -Description "AIService interpreter"
Assert-PythonVersionPrefix -PythonExe $aiPython -ExpectedPrefix "3.11" -ServiceName "AIService"
Assert-CommandSuccess "AIService pip check" {
    & $aiPython -m pip check
}
Assert-CommandSuccess "AIService torch and CUDA check" {
    & $aiPython -c "import torch; print('torch=' + torch.__version__); print('cuda=' + str(torch.cuda.is_available())); print('gpu=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'))"
}
Run-ImportCheck -PythonExe $aiPython -ModuleName "cv2"
Run-ImportCheck -PythonExe $aiPython -ModuleName "ultralytics"
Run-ImportCheck -PythonExe $aiPython -ModuleName "insightface"
Assert-CommandSuccess "Import onnxruntime" {
    & $aiPython -c "import onnxruntime; print('onnxruntime=' + onnxruntime.__version__)"
}

Write-Host ""
Write-Host "[Backend]"
Assert-FileExists -Path $backendPython -Description "Backend interpreter"
Assert-CommandSuccess "Backend Python version" {
    & $backendPython --version
}
Assert-CommandSuccess "Backend pip check" {
    & $backendPython -m pip check
}
Push-Location $backendDir
try {
    Assert-CommandSuccess "Backend manage.py check" {
        & $backendPython manage.py check
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "[FactoryVision] Python environment checks passed."
