param(
  [string]$BindHost = "127.0.0.1",
  [int]$BackendPort = 8002,
  [int]$FrontendPort = 5173,
  [int]$TailLines = 200,
  [switch]$Detached,
  [string]$RunId
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
  $root = Resolve-Path (Join-Path $PSScriptRoot "..")
  return $root.Path
}

function New-LogDir {
  param([string]$Root)
  $runId = if ($RunId) { $RunId } else { Get-Date -Format "yyyyMMdd-HHmmss" }
  $dir = Join-Path $Root ("logs\\dev-watch\\" + $runId)
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  return $dir
}

function Write-WatchLog {
  param(
    [string]$Path,
    [string]$Message
  )
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $line = "[$ts] $Message"
  Add-Content -Path $Path -Value $line
  Write-Host $line
}

function Tail-To-WatchLog {
  param(
    [string]$WatchLog,
    [string]$Label,
    [string]$Path,
    [int]$Lines
  )
  if (Test-Path $Path) {
    Write-WatchLog -Path $WatchLog -Message "$Label tail (last $Lines lines) from $Path"
    Get-Content -Path $Path -Tail $Lines | ForEach-Object {
      Add-Content -Path $WatchLog -Value ("  " + $_)
    }
  } else {
    Write-WatchLog -Path $WatchLog -Message "$Label log missing: $Path"
  }
}

function Start-Backend {
  param(
    [string]$Root,
    [string]$BindHost,
    [int]$Port,
    [string]$LogDir,
    [string]$WatchLog
  )
  $backendDir = Join-Path $Root "backend"
  $pythonExe = Join-Path $backendDir ".venv\\Scripts\\python.exe"
  if (!(Test-Path $pythonExe)) {
    throw "python exe not found: $pythonExe"
  }

  $out = Join-Path $LogDir "backend.out.log"
  $err = Join-Path $LogDir "backend.err.log"

  $oldHost = $env:HOST
  $oldPort = $env:API_PORT
  $env:HOST = $BindHost
  $env:API_PORT = "$Port"
  try {
  $proc = Start-Process -FilePath $pythonExe -ArgumentList "run_dev.py" -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
  } finally {
    $env:HOST = $oldHost
    $env:API_PORT = $oldPort
  }

  Write-WatchLog -Path $WatchLog -Message "Backend started pid=$($proc.Id) out=$out err=$err"
  return $proc
}

function Start-Frontend {
  param(
    [string]$Root,
    [string]$BindHost,
    [int]$Port,
    [string]$LogDir,
    [string]$WatchLog
  )
  $frontendDir = Join-Path $Root "frontend"
  $pnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
  if (-not $pnpmCmd) {
    throw "pnpm not found in PATH"
  }

  $out = Join-Path $LogDir "frontend.out.log"
  $err = Join-Path $LogDir "frontend.err.log"
  $args = @("/c", "pnpm", "dev", "--host", $BindHost, "--port", "$Port")
  $proc = Start-Process -FilePath "cmd.exe" -ArgumentList $args -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
  Write-WatchLog -Path $WatchLog -Message "Frontend started pid=$($proc.Id) out=$out err=$err"
  return $proc
}

if (-not $Detached) {
  $repoRoot = Get-RepoRoot
  $runId = if ($RunId) { $RunId } else { Get-Date -Format "yyyyMMdd-HHmmss" }
  $logDir = Join-Path $repoRoot ("logs\\dev-watch\\" + $runId)
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $scriptPath = $MyInvocation.MyCommand.Path
  $args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $scriptPath,
    "-Detached",
    "-BindHost", $BindHost,
    "-BackendPort", $BackendPort,
    "-FrontendPort", $FrontendPort,
    "-TailLines", $TailLines,
    "-RunId", $runId
  )
  Start-Process -FilePath "pwsh" -ArgumentList $args -WindowStyle Hidden | Out-Null
  Write-Host "Dev watch started in background."
  Write-Host "Logs dir: $logDir"
  return
}

$repoRoot = Get-RepoRoot
$logDir = New-LogDir -Root $repoRoot
$watchLog = Join-Path $logDir "watch.log"

Write-WatchLog -Path $watchLog -Message "Dev watch started. host=$BindHost backendPort=$BackendPort frontendPort=$FrontendPort"
Write-WatchLog -Path $watchLog -Message "Logs dir: $logDir"

$backend = Start-Backend -Root $repoRoot -BindHost $BindHost -Port $BackendPort -LogDir $logDir -WatchLog $watchLog
$frontend = Start-Frontend -Root $repoRoot -BindHost $BindHost -Port $FrontendPort -LogDir $logDir -WatchLog $watchLog

while ($true) {
  Start-Sleep -Seconds 1

  if ($backend.HasExited) {
    Write-WatchLog -Path $watchLog -Message "Backend exited code=$($backend.ExitCode)"
    Tail-To-WatchLog -WatchLog $watchLog -Label "backend.err" -Path (Join-Path $logDir "backend.err.log") -Lines $TailLines
    Tail-To-WatchLog -WatchLog $watchLog -Label "backend.out" -Path (Join-Path $logDir "backend.out.log") -Lines $TailLines
    if (-not $frontend.HasExited) {
      Write-WatchLog -Path $watchLog -Message "Stopping frontend pid=$($frontend.Id)"
      Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    }
    break
  }

  if ($frontend.HasExited) {
    Write-WatchLog -Path $watchLog -Message "Frontend exited code=$($frontend.ExitCode)"
    Tail-To-WatchLog -WatchLog $watchLog -Label "frontend.err" -Path (Join-Path $logDir "frontend.err.log") -Lines $TailLines
    Tail-To-WatchLog -WatchLog $watchLog -Label "frontend.out" -Path (Join-Path $logDir "frontend.out.log") -Lines $TailLines
    if (-not $backend.HasExited) {
      Write-WatchLog -Path $watchLog -Message "Stopping backend pid=$($backend.Id)"
      Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
    break
  }
}

Write-WatchLog -Path $watchLog -Message "Dev watch stopped."
