param(
  [string]$ServerUrl = "http://localhost:8080",
  [string]$CsvPath = "",
  [int]$WarmupRuns = 3,
  [int]$MeasuredRuns = 10,
  [string]$OutDir = "",
  [string]$Label = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-DefaultCsvPath {
  param([string]$ScriptDir)
  $candidate = [System.IO.Path]::GetFullPath((Join-Path $ScriptDir "..\..\dataset\20180713-home2mimos_clean.csv"))
  if (Test-Path -LiteralPath $candidate) { return $candidate }
  throw "CSV path not provided and default dataset not found at: $candidate"
}

function Percentile {
  param(
    [double[]]$Values,
    [double]$P
  )
  if ($Values.Count -eq 0) { return [double]::NaN }
  $sorted = $Values | Sort-Object
  if ($sorted.Count -eq 1) { return [double]$sorted[0] }

  $rank = ($P / 100.0) * ($sorted.Count - 1)
  $lower = [math]::Floor($rank)
  $upper = [math]::Ceiling($rank)
  if ($lower -eq $upper) {
    return [double]$sorted[$lower]
  }
  $weight = $rank - $lower
  return ([double]$sorted[$lower]) + (([double]$sorted[$upper] - [double]$sorted[$lower]) * $weight)
}

function StdDevSample {
  param([double[]]$Values)
  if ($Values.Count -lt 2) { return 0.0 }
  $mean = [double](($Values | Measure-Object -Average).Average)
  $sumSq = 0.0
  foreach ($v in $Values) {
    $d = ([double]$v) - $mean
    $sumSq += ($d * $d)
  }
  return [math]::Sqrt($sumSq / ($Values.Count - 1))
}

function Sum-Flags {
  param([object[]]$Runs)
  $totals = @{}
  foreach ($r in $Runs) {
    if ($null -eq $r.flags) { continue }
    foreach ($p in $r.flags.PSObject.Properties) {
      $k = [string]$p.Name
      $v = [int64]$p.Value
      if ($totals.ContainsKey($k)) { $totals[$k] += $v } else { $totals[$k] = $v }
    }
  }
  return [PSCustomObject]$totals
}

function Invoke-Analyze {
  param(
    [string]$Url,
    [string]$FilePath,
    [bool]$RvEnabled
  )
  $rvValue = if ($RvEnabled) { "true" } else { "false" }
  $endpoint = "$Url/api/rv/analyze?rvEnabled=$rvValue"
  $tmpBody = [System.IO.Path]::GetTempFileName()
  try {
    $status = curl.exe -sS -o $tmpBody -w "%{http_code}" -X POST $endpoint -F "file=@$FilePath"
    $body = Get-Content -Raw -Path $tmpBody
  } finally {
    if (Test-Path -LiteralPath $tmpBody) { Remove-Item -LiteralPath $tmpBody -Force }
  }

  if ([string]::IsNullOrWhiteSpace($body)) {
    throw "Empty response from endpoint: $endpoint"
  }

  if ($status -ne "200") {
    throw "Endpoint returned HTTP $status at $endpoint. Body: $body"
  }

  try {
    $obj = $body | ConvertFrom-Json
  } catch {
    throw "Invalid JSON from endpoint $endpoint. Body: $body"
  }

  $hasElapsed = $obj.PSObject.Properties.Name -contains "elapsedMs"
  $hasRows = $obj.PSObject.Properties.Name -contains "rowsProcessed"
  if (-not $hasElapsed -or -not $hasRows) {
    throw "Response missing expected fields (elapsedMs/rowsProcessed) from $endpoint. Body: $body"
  }

  return $obj
}

function Build-ModeSummary {
  param(
    [string]$ModeName,
    [object[]]$Runs
  )
  if ($Runs.Count -eq 0) {
    throw "No runs available for mode: $ModeName"
  }

  $elapsed = @()
  $throughputs = @()
  foreach ($r in $Runs) {
    $ms = [double]$r.elapsedMs
    $rows = [double]$r.rowsProcessed
    $elapsed += $ms
    if ($ms -gt 0) {
      $throughputs += ($rows / ($ms / 1000.0))
    } else {
      $throughputs += [double]::PositiveInfinity
    }
  }

  $avgElapsed = [double](($elapsed | Measure-Object -Average).Average)
  $avgThroughput = [double](($throughputs | Measure-Object -Average).Average)
  $stdElapsed = StdDevSample -Values $elapsed
  $stdThroughput = StdDevSample -Values $throughputs
  $rowsProcessed = [int64]$Runs[-1].rowsProcessed
  $p95 = Percentile -Values $elapsed -P 95
  $p99 = Percentile -Values $elapsed -P 99
  $flagsTotal = Sum-Flags -Runs $Runs

  return [PSCustomObject]@{
    mode = $ModeName
    runs = $Runs.Count
    rowsProcessed = $rowsProcessed
    avgElapsedMs = $avgElapsed
    stddevElapsedMs = $stdElapsed
    avgRowsPerSec = $avgThroughput
    stddevRowsPerSec = $stdThroughput
    p95ElapsedMs = $p95
    p99ElapsedMs = $p99
    flagsTotal = $flagsTotal
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($CsvPath)) {
  $CsvPath = Resolve-DefaultCsvPath -ScriptDir $scriptDir
}
$CsvPath = [System.IO.Path]::GetFullPath($CsvPath)
if (-not (Test-Path -LiteralPath $CsvPath)) {
  throw "CSV file not found: $CsvPath"
}

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $suffix = if ([string]::IsNullOrWhiteSpace($Label)) { $timestamp } else { "$timestamp-$Label" }
  $OutDir = Join-Path $scriptDir "runs\$suffix"
}
[System.IO.Directory]::CreateDirectory($OutDir) | Out-Null

Write-Host "Benchmarking endpoint with file: $CsvPath"
Write-Host "Server: $ServerUrl  Warmup: $WarmupRuns  Measured: $MeasuredRuns"
Write-Host ""

Write-Host "Warmup phase..."
1..$WarmupRuns | ForEach-Object {
  Invoke-Analyze -Url $ServerUrl -FilePath $CsvPath -RvEnabled $true | Out-Null
  Invoke-Analyze -Url $ServerUrl -FilePath $CsvPath -RvEnabled $false | Out-Null
}

$rvOnRuns = @()
$rvOffRuns = @()

Write-Host "Measured phase..."
1..$MeasuredRuns | ForEach-Object {
  $i = $_
  $on = Invoke-Analyze -Url $ServerUrl -FilePath $CsvPath -RvEnabled $true
  $off = Invoke-Analyze -Url $ServerUrl -FilePath $CsvPath -RvEnabled $false
  $rvOnRuns += $on
  $rvOffRuns += $off
  Write-Host ("Run {0,2}: on={1}ms off={2}ms rows={3}" -f $i, $on.elapsedMs, $off.elapsedMs, $on.rowsProcessed)
}

$summaryOn = Build-ModeSummary -ModeName "rv_on" -Runs $rvOnRuns
$summaryOff = Build-ModeSummary -ModeName "rv_off" -Runs $rvOffRuns

$overheadPct = (($summaryOn.avgElapsedMs - $summaryOff.avgElapsedMs) / $summaryOff.avgElapsedMs) * 100.0

$report = [PSCustomObject]@{
  createdAt = (Get-Date).ToString("o")
  label = $Label
  serverUrl = $ServerUrl
  csvPath = $CsvPath
  warmupRuns = $WarmupRuns
  measuredRuns = $MeasuredRuns
  rvOn = $summaryOn
  rvOff = $summaryOff
  overheadPct = $overheadPct
}

$jsonPath = Join-Path $OutDir "benchmark-summary.json"
$csvPathOut = Join-Path $OutDir "benchmark-runs.csv"

$runRows = @()
for ($i = 0; $i -lt $MeasuredRuns; $i++) {
  $on = $rvOnRuns[$i]
  $off = $rvOffRuns[$i]
  $runRows += [PSCustomObject]@{
    run = $i + 1
    onElapsedMs = [double]$on.elapsedMs
    offElapsedMs = [double]$off.elapsedMs
    onRowsProcessed = [int64]$on.rowsProcessed
    offRowsProcessed = [int64]$off.rowsProcessed
    onRowsPerSec = if ([double]$on.elapsedMs -gt 0) { [double]$on.rowsProcessed / ([double]$on.elapsedMs / 1000.0) } else { [double]::PositiveInfinity }
    offRowsPerSec = if ([double]$off.elapsedMs -gt 0) { [double]$off.rowsProcessed / ([double]$off.elapsedMs / 1000.0) } else { [double]::PositiveInfinity }
  }
}

$report | ConvertTo-Json -Depth 8 | Out-File -Encoding UTF8 $jsonPath
$runRows | Export-Csv -NoTypeInformation -Encoding UTF8 $csvPathOut

Write-Host ""
Write-Host "=== Benchmark Summary ==="
Write-Host ("rowsProcessed={0}" -f $summaryOn.rowsProcessed)
Write-Host ("avgOnMs={0:N2} avgOffMs={1:N2}" -f $summaryOn.avgElapsedMs, $summaryOff.avgElapsedMs)
Write-Host ("stdOnMs={0:N2} stdOffMs={1:N2}" -f $summaryOn.stddevElapsedMs, $summaryOff.stddevElapsedMs)
Write-Host ("avgOnRowsPerSec={0:N2} avgOffRowsPerSec={1:N2}" -f $summaryOn.avgRowsPerSec, $summaryOff.avgRowsPerSec)
Write-Host ("stdOnRowsPerSec={0:N2} stdOffRowsPerSec={1:N2}" -f $summaryOn.stddevRowsPerSec, $summaryOff.stddevRowsPerSec)
Write-Host ("p95OnMs={0:N2} p95OffMs={1:N2}" -f $summaryOn.p95ElapsedMs, $summaryOff.p95ElapsedMs)
Write-Host ("p99OnMs={0:N2} p99OffMs={1:N2}" -f $summaryOn.p99ElapsedMs, $summaryOff.p99ElapsedMs)
Write-Host ("overheadPct={0:N2}" -f $overheadPct)
Write-Host ""
Write-Host "Saved:"
Write-Host " - $jsonPath"
Write-Host " - $csvPathOut"
