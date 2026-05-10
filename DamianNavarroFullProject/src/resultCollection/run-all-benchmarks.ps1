param(
  [int]$ServerPort = 18081,
  [int]$WarmupRuns = 3,
  [int]$MeasuredRuns = 10,
  [switch]$ForceRegenerateAbnormal
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-AllowedPort {
  param([int]$Port)
  if ($Port -eq 8080 -or $Port -eq 8082) {
    throw "Refusing to use port $Port. Please use a non-conflicting port (not 8080/8082)."
  }
}

function Test-TcpPortOpen {
  param(
    [string]$HostName,
    [int]$Port
  )
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $iar = $client.BeginConnect($HostName, $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(500)
    if (-not $ok) { return $false }
    $client.EndConnect($iar) | Out-Null
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Wait-ForPort {
  param(
    [string]$HostName,
    [int]$Port,
    [int]$TimeoutSeconds = 120
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-TcpPortOpen -HostName $HostName -Port $Port) {
      return
    }
    Start-Sleep -Milliseconds 500
  }
  throw "Timed out waiting for ${HostName}:${Port} to become reachable."
}

Assert-AllowedPort -Port $ServerPort

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))
$springDir = Join-Path $repoRoot "src\SpringServer"
$datasetDir = Join-Path $repoRoot "dataset"
$normalCsv = Join-Path $datasetDir "20180713-home2mimos_clean.csv"
$abnormalCsv = Join-Path $datasetDir "20180713-home2mimos_clean_abnormal.csv"
$benchmarkScript = Join-Path $scriptDir "benchmark-rv.ps1"
$injectScript = Join-Path $scriptDir "inject_violations.py"

if (-not (Test-Path -LiteralPath $normalCsv)) {
  throw "Normal dataset not found: $normalCsv"
}
if (-not (Test-Path -LiteralPath $benchmarkScript)) {
  throw "Benchmark script not found: $benchmarkScript"
}
if (-not (Test-Path -LiteralPath $injectScript)) {
  throw "Injector script not found: $injectScript"
}

if (Test-TcpPortOpen -HostName "127.0.0.1" -Port $ServerPort) {
  throw "Port $ServerPort is already in use. Pick another port with -ServerPort."
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$sessionDir = Join-Path $scriptDir "runs\session-$timestamp"
[System.IO.Directory]::CreateDirectory($sessionDir) | Out-Null

$serverOut = Join-Path $sessionDir "server.out.log"
$serverErr = Join-Path $sessionDir "server.err.log"
$combinedReport = Join-Path $sessionDir "combined-summary.txt"
$serverUrl = "http://localhost:$ServerPort"
$serverProc = $null

Write-Host "Session folder: $sessionDir"
Write-Host "Starting Spring server on $serverUrl ..."

try {
  Push-Location $springDir
  $serverProc = Start-Process `
    -FilePath "mvn" `
    -ArgumentList @("spring-boot:run", "-Dspring-boot.run.arguments=--server.port=$ServerPort") `
    -RedirectStandardOutput $serverOut `
    -RedirectStandardError $serverErr `
    -PassThru
  Pop-Location

  Wait-ForPort -HostName "127.0.0.1" -Port $ServerPort -TimeoutSeconds 150
  Write-Host "Server is reachable."

  if ($ForceRegenerateAbnormal -or -not (Test-Path -LiteralPath $abnormalCsv)) {
    Write-Host "Generating abnormal dataset..."
    & python $injectScript --input $normalCsv --output $abnormalCsv --summary (Join-Path $datasetDir "violations_summary.txt")
  } else {
    Write-Host "Using existing abnormal dataset: $abnormalCsv"
  }

  Write-Host "Running baseline benchmark..."
  & $benchmarkScript `
    -ServerUrl $serverUrl `
    -CsvPath $normalCsv `
    -WarmupRuns $WarmupRuns `
    -MeasuredRuns $MeasuredRuns `
    -OutDir (Join-Path $sessionDir "baseline") `
    -Label "baseline"

  Write-Host "Running abnormal benchmark..."
  & $benchmarkScript `
    -ServerUrl $serverUrl `
    -CsvPath $abnormalCsv `
    -WarmupRuns $WarmupRuns `
    -MeasuredRuns $MeasuredRuns `
    -OutDir (Join-Path $sessionDir "abnormal") `
    -Label "abnormal"

  $baselineJson = Join-Path $sessionDir "baseline\benchmark-summary.json"
  $abnormalJson = Join-Path $sessionDir "abnormal\benchmark-summary.json"

  $base = Get-Content -Raw -Path $baselineJson | ConvertFrom-Json
  $abn = Get-Content -Raw -Path $abnormalJson | ConvertFrom-Json

  $lines = @()
  $lines += "Combined benchmark summary"
  $lines += "createdAt=$((Get-Date).ToString("o"))"
  $lines += "serverUrl=$serverUrl"
  $lines += "normalCsv=$normalCsv"
  $lines += "abnormalCsv=$abnormalCsv"
  $lines += "warmupRuns=$WarmupRuns"
  $lines += "measuredRuns=$MeasuredRuns"
  $lines += ""
  $lines += "[baseline]"
  $lines += "rowsProcessed=$($base.rvOn.rowsProcessed)"
  $lines += "avgOnMs=$($base.rvOn.avgElapsedMs) avgOffMs=$($base.rvOff.avgElapsedMs) overheadPct=$($base.overheadPct)"
  $lines += "avgOnCpuMs=$($base.rvOn.avgCpuMs) avgOffCpuMs=$($base.rvOff.avgCpuMs)"
  $lines += "avgOnHeapDeltaMB=$([double]$base.rvOn.avgHeapDeltaBytes / 1MB) avgOffHeapDeltaMB=$([double]$base.rvOff.avgHeapDeltaBytes / 1MB)"
  $lines += "stdOnMs=$($base.rvOn.stddevElapsedMs) stdOffMs=$($base.rvOff.stddevElapsedMs)"
  $lines += "avgOnRowsPerSec=$($base.rvOn.avgRowsPerSec) avgOffRowsPerSec=$($base.rvOff.avgRowsPerSec)"
  $lines += "stdOnRowsPerSec=$($base.rvOn.stddevRowsPerSec) stdOffRowsPerSec=$($base.rvOff.stddevRowsPerSec)"
  $lines += ""
  $lines += "[abnormal]"
  $lines += "rowsProcessed=$($abn.rvOn.rowsProcessed)"
  $lines += "avgOnMs=$($abn.rvOn.avgElapsedMs) avgOffMs=$($abn.rvOff.avgElapsedMs) overheadPct=$($abn.overheadPct)"
  $lines += "avgOnCpuMs=$($abn.rvOn.avgCpuMs) avgOffCpuMs=$($abn.rvOff.avgCpuMs)"
  $lines += "avgOnHeapDeltaMB=$([double]$abn.rvOn.avgHeapDeltaBytes / 1MB) avgOffHeapDeltaMB=$([double]$abn.rvOff.avgHeapDeltaBytes / 1MB)"
  $lines += "stdOnMs=$($abn.rvOn.stddevElapsedMs) stdOffMs=$($abn.rvOff.stddevElapsedMs)"
  $lines += "avgOnRowsPerSec=$($abn.rvOn.avgRowsPerSec) avgOffRowsPerSec=$($abn.rvOff.avgRowsPerSec)"
  $lines += "stdOnRowsPerSec=$($abn.rvOn.stddevRowsPerSec) stdOffRowsPerSec=$($abn.rvOff.stddevRowsPerSec)"
  $lines += "rvOnFlagsTotal=$($abn.rvOn.flagsTotal | ConvertTo-Json -Compress)"

  $lines | Out-File -FilePath $combinedReport -Encoding UTF8

  Write-Host ""
  Write-Host "All done."
  Write-Host "Results saved under: $sessionDir"
  Write-Host " - baseline\benchmark-summary.json"
  Write-Host " - baseline\benchmark-runs.csv"
  Write-Host " - abnormal\benchmark-summary.json"
  Write-Host " - abnormal\benchmark-runs.csv"
  Write-Host " - combined-summary.txt"
  Write-Host "Server logs:"
  Write-Host " - server.out.log"
  Write-Host " - server.err.log"
}
finally {
  if ($null -ne $serverProc -and -not $serverProc.HasExited) {
    Write-Host "Stopping Spring server (PID $($serverProc.Id))..."
    Stop-Process -Id $serverProc.Id -Force
  }
}

