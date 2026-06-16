param(
    [switch]$FrontendOnly,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Continue"
$pythonPath = "D:\henv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) { $pythonPath = "python" }

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($scriptDir)) { $scriptDir = (Get-Item .).FullName }

Write-Host "=== AI Career Studio ===" -ForegroundColor Cyan

# ── Step 1: Kill EVERYTHING on port 8000 ─────────────────────────────────────
if (-not $FrontendOnly) {
    Write-Host "`n[1/3] Clearing port 8000..." -ForegroundColor Yellow

    $lines = netstat -ano 2>$null | Where-Object { $_ -match "[:\.]8000\s" }
    if ($lines) {
        $pids8000 = $lines |
            ForEach-Object { ($_ -split '\s+') | Select-Object -Last 1 } |
            Where-Object { $_ -match '^\d+$' -and $_ -ne '0' } |
            Sort-Object -Unique

        Write-Host "  PIDs on 8000: $($pids8000 -join ', ')" -ForegroundColor Gray
        foreach ($p in $pids8000) {
            taskkill /F /PID $p 2>$null | Out-Null
            Write-Host "  Killed PID $p" -ForegroundColor Gray
        }
        Start-Sleep -Seconds 2
    }

    # If still occupied (WSL2/Hyper-V entries), try service-level release
    $still = netstat -ano 2>$null | Where-Object { $_ -match "[:\.]8000\s" }
    if ($still) {
        Write-Host "  Port still held — trying WSL/Hyper-V port proxy removal..." -ForegroundColor Yellow
        netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0   2>$null | Out-Null
        netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=127.0.0.1 2>$null | Out-Null

        try { Restart-Service WinNat -Force -ErrorAction Stop; Write-Host "  WinNat restarted." -ForegroundColor Gray }
        catch { Write-Host "  WinNat not running (ok)." -ForegroundColor DarkGray }

        Start-Sleep -Seconds 3
        $still2 = netstat -ano 2>$null | Where-Object { $_ -match "[:\.]8000\s" }
        if ($still2) {
            Write-Host "  WARNING: Port 8000 still reserved by system process." -ForegroundColor Red
            Write-Host "  Run this script as Administrator for full release." -ForegroundColor Red
            Write-Host "  Attempting to start on 8000 anyway..." -ForegroundColor Yellow
        } else {
            Write-Host "  Port 8000 cleared." -ForegroundColor Green
        }
    } else {
        Write-Host "  Port 8000 is free." -ForegroundColor Green
    }
}

# ── Step 2: Set frontend env to port 8000 ────────────────────────────────────
if (-not $BackendOnly) {
    Write-Host "`n[2/3] Setting frontend API URL -> http://localhost:8000/api ..." -ForegroundColor Yellow
    $envFile = Join-Path $scriptDir "frontend\.env.local"
    Set-Content -Path $envFile -Value "VITE_API_BASE_URL=http://localhost:8000/api" -Encoding UTF8
    Write-Host "  Written: $envFile" -ForegroundColor Green
    Write-Host "  Restart Vite (npm run dev) if it was already running." -ForegroundColor Cyan
}

# ── Step 3: Start backend on port 8000 ───────────────────────────────────────
if (-not $FrontendOnly) {
    Write-Host "`n[3/3] Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
    Write-Host "  API docs  -> http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "  Press Ctrl+C to stop.`n" -ForegroundColor Gray

    $backendDir = Join-Path $scriptDir "backend"
    Set-Location $backendDir
    & $pythonPath -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
}
