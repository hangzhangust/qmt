# QMT Service Status Checker
# Check if frontend and backend services are running

function Test-PortInUse {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        return ($connection -ne $null)
    }
    catch {
        return $false
    }
}

function Get-ProcessOnPort {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($connection) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            return $process
        }
        return $null
    }
    catch {
        return $null
    }
}

function Test-HttpEndpoint {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Show-ServiceStatus {
    param(
        [string]$ServiceName,
        [int]$Port,
        [string]$HealthUrl
    )

    $portInUse = Test-PortInUse -Port $Port

    Write-Host "`n$ServiceName (Port $Port):" -ForegroundColor Yellow

    if ($portInUse) {
        $process = Get-ProcessOnPort -Port $Port
        if ($process) {
            Write-Host "  [OK] Running" -ForegroundColor Green
            Write-Host "    Process: $($process.ProcessName) (PID: $($process.Id))"

            if ($HealthUrl) {
                $isHealthy = Test-HttpEndpoint -Url $HealthUrl
                if ($isHealthy) {
                    Write-Host "    Health Check: OK" -ForegroundColor Green
                }
                else {
                    Write-Host "    Health Check: Failed (service may not be fully started)" -ForegroundColor Red
                }
            }
        }
        else {
            Write-Host "  [WARNING] Port in use, but cannot get process info" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "  [STOPPED] Not running" -ForegroundColor Red

        if ($ServiceName -eq "Backend Service") {
            Write-Host "    Hint: Go to backend directory and run 'python main.py'"
        }
        elseif ($ServiceName -eq "Frontend Service") {
            Write-Host "    Hint: Go to frontend directory and run 'npm run dev'"
        }
    }
}

function Main {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  QMT Service Status Check Report" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    Write-Host "`nCheck Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"

    Show-ServiceStatus -ServiceName "Backend Service" -Port 8000 -HealthUrl "http://127.0.0.1:8000/health"
    Show-ServiceStatus -ServiceName "Frontend Service" -Port 3000 -HealthUrl $null

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "`nAccess URLs:" -ForegroundColor Yellow
    Write-Host "  - Backend API Docs: http://127.0.0.1:8000/docs"
    Write-Host "  - Backend Health: http://127.0.0.1:8000/health"
    Write-Host "  - Frontend: http://localhost:3000"
    Write-Host "`n========================================" -ForegroundColor Cyan

    Write-Host "`nQuick Actions:" -ForegroundColor Yellow
    Write-Host "  1. Start Dev Environment: .\start_dev.bat"
    Write-Host "  2. Start Production: .\start_prod.bat"
    Write-Host "  3. Stop All Services: .\stop_services.bat"
    Write-Host "  4. View Guide: notepad SERVICES_GUIDE.md`n"

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "`nDependency Check:" -ForegroundColor Yellow

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonVersion = python --version 2>&1
        Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
    }
    else {
        Write-Host "  [ERROR] Python: Not installed or not in PATH" -ForegroundColor Red
    }

    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) {
        $nodeVersion = node --version
        Write-Host "  [OK] Node.js: $nodeVersion" -ForegroundColor Green
    }
    else {
        Write-Host "  [ERROR] Node.js: Not installed or not in PATH" -ForegroundColor Red
    }

    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd) {
        $npmVersion = npm --version
        Write-Host "  [OK] npm: $npmVersion" -ForegroundColor Green
    }
    else {
        Write-Host "  [ERROR] npm: Not installed or not in PATH" -ForegroundColor Red
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host ""
}

Main
