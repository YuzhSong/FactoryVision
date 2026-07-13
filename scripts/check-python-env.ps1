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

function Read-PythonVersion {
    param([string]$PythonExe)

    $version = & $PythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    if ($LASTEXITCODE -eq 0) {
        return $version
    }
    return $null
}

function Get-VenvBasePython {
    param([string]$VenvDir)

    $pyvenvCfg = Join-Path $VenvDir "pyvenv.cfg"
    if (-not (Test-Path -LiteralPath $pyvenvCfg)) {
        return $null
    }

    $cfg = Get-Content -LiteralPath $pyvenvCfg
    $executableLine = $cfg | Where-Object { $_ -match "^executable\s*=" } | Select-Object -First 1
    if ($executableLine) {
        $executable = ($executableLine -replace "^executable\s*=\s*", "").Trim()
        if ($executable) {
            return $executable
        }
    }

    $homeLine = $cfg | Where-Object { $_ -match "^home\s*=" } | Select-Object -First 1
    if ($homeLine) {
        $home = ($homeLine -replace "^home\s*=\s*", "").Trim()
        if ($home) {
            return (Join-Path $home "python.exe")
        }
    }

    return $null
}

function Repair-VenvLauncher {
    param(
        [string]$VenvDir,
        [string]$ServiceName
    )

    $basePython = Get-VenvBasePython -VenvDir $VenvDir
    if (-not $basePython -or -not (Test-Path -LiteralPath $basePython)) {
        Fail "$ServiceName venv launcher is broken and its base interpreter was not found. Restore the required Python runtime, then run: <required Python> -m venv --upgrade $VenvDir"
    }

    $baseVersion = Read-PythonVersion -PythonExe $basePython
    if (-not $baseVersion) {
        Fail "$ServiceName venv launcher is broken and its base interpreter cannot run: $basePython"
    }

    Write-Host "$ServiceName venv launcher repair: $basePython"
    & $basePython -m venv --upgrade $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Fail "$ServiceName venv launcher repair failed."
    }
}

function Assert-PythonVersionPrefix {
    param(
        [string]$PythonExe,
        [string]$ExpectedPrefix,
        [string]$ServiceName
    )

    $version = Read-PythonVersion -PythonExe $PythonExe
    if (-not $version) {
        $venvDir = Split-Path -Parent (Split-Path -Parent $PythonExe)
        Repair-VenvLauncher -VenvDir $venvDir -ServiceName $ServiceName
        $version = Read-PythonVersion -PythonExe $PythonExe
    }
    if (-not $version) {
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
