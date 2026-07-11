param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

function Assert-PortAvailable {
    param([int]$Port, [string]$ServiceName)

    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $listener) {
        Fail "$ServiceName cannot start because port $Port is already in use (PID $($listener.OwningProcess)). Stop that service first."
    }
}

$repoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
$scriptDir = Join-Path $repoRoot "scripts"
$runtimeDir = Join-Path $repoRoot ".codex-runlogs"
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

Assert-PortAvailable -Port 8000 -ServiceName "Backend"
Assert-PortAvailable -Port 9000 -ServiceName "AIService"
if (-not $SkipFrontend) {
    Assert-PortAvailable -Port 5175 -ServiceName "Frontend"
}

$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$started = @()

function Start-ServiceScript {
    param([string]$Name, [string]$ScriptName)

    $outLog = Join-Path $runtimeDir "$Name.out.log"
    $errLog = Join-Path $runtimeDir "$Name.err.log"
    $process = Start-Process -FilePath $powershell -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $scriptDir $ScriptName)
    ) -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
    $script:started += [pscustomobject]@{ name = $Name; processId = $process.Id }
}

Start-ServiceScript -Name "backend" -ScriptName "start-backend.ps1"
Start-ServiceScript -Name "ai-service" -ScriptName "start-ai-service.ps1"
if (-not $SkipFrontend) {
    Start-ServiceScript -Name "frontend" -ScriptName "start-frontend.ps1"
}

$started | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $runtimeDir "local-dev-processes.json")
Write-Host "[FactoryVision] Started local services."
Write-Host "Frontend:  http://127.0.0.1:5175/monitor"
Write-Host "Backend:   http://127.0.0.1:8000/api/health/"
Write-Host "AIService: http://127.0.0.1:9000/health"
Write-Host "Logs:      $runtimeDir"
