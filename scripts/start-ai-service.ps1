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
$pyvenvCfg = Join-Path $serviceDir ".venv\pyvenv.cfg"
$envFile = Join-Path $serviceDir ".env.local"
$localAiToken = "factoryvision-local-e2e-token"

function Import-EnvFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) {
            return
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Import-EnvFile -Path $envFile

if (-not $env:BACKEND_API_TOKEN) {
    $env:BACKEND_API_TOKEN = $localAiToken
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Fail "AIService interpreter not found: $pythonExe"
}

function Get-VenvBasePython {
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

function Read-PythonVersion {
    param([string]$PythonPath)

    $output = & $PythonPath -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    if ($LASTEXITCODE -eq 0) {
        return $output
    }
    return $null
}

function Repair-VenvLauncher {
    $basePython = Get-VenvBasePython
    if (-not $basePython -or -not (Test-Path -LiteralPath $basePython)) {
        Fail "AIService venv launcher is broken and its Python 3.11 base interpreter was not found. Reinstall/restore Python 3.11, then run: <Python 3.11> -m venv --upgrade ai-service/.venv"
    }

    $baseVersion = Read-PythonVersion -PythonPath $basePython
    if (-not $baseVersion -or -not $baseVersion.StartsWith("3.11")) {
        Fail "AIService venv launcher is broken and pyvenv.cfg points to a non-3.11 base interpreter: $basePython ($baseVersion)."
    }

    Write-Host "[FactoryVision] Repairing AIService venv launcher with $basePython"
    & $basePython -m venv --upgrade (Join-Path $serviceDir ".venv")
    if ($LASTEXITCODE -ne 0) {
        Fail "AIService venv launcher repair failed."
    }
}

$version = Read-PythonVersion -PythonPath $pythonExe
if (-not $version) {
    Repair-VenvLauncher
    $version = Read-PythonVersion -PythonPath $pythonExe
}
if (-not $version) {
    Fail "AIService interpreter failed while reading Python version."
}
if (-not $version.StartsWith("3.11")) {
    Fail "AIService must use Python 3.11.x, got $version."
}

Write-Host "[FactoryVision] Starting AIService with $pythonExe"
Write-Host "[FactoryVision] Python version: $version"
Write-Host "[FactoryVision] Backend API: $env:BACKEND_API_BASE_URL"
$env:MODEL_WARMUP_ON_STARTUP = "True"

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
