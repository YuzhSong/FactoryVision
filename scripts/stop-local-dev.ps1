$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")).Path
$stateFile = Join-Path $repoRoot ".codex-runlogs\local-dev-processes.json"

if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host "[FactoryVision] No local-dev process state file was found."
    exit 0
}

$services = Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json
foreach ($service in @($services)) {
    $process = Get-Process -Id $service.processId -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        continue
    }
    & taskkill.exe /PID $service.processId /T /F | Out-Null
    Write-Host "[FactoryVision] Stopped $($service.name) (PID $($service.processId))."
}

Remove-Item -LiteralPath $stateFile -Force
