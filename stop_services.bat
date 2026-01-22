@echo off
REM QMT 量化交易系统 - 服务停止脚本
REM 用于停止前后端服务

chcp 65001 >nul
setlocal enabledelayedexpansion

title QMT 服务停止器

echo ========================================
echo   QMT 量化交易系统 - 停止服务
echo ========================================
echo.
echo 正在检查并停止服务...
echo.

REM 停止后端服务(端口 8000)
echo [1/2] 检查后端服务(端口 8000)...
set "backend_found=0"

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    set "backend_pid=%%a"
    set "backend_found=1"
    echo [√] 发现后端服务(PID: %%a)

    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo [!] 无法终止进程 %%a,可能需要管理员权限
    ) else (
        echo [√] 后端服务已停止
    )
)

if !backend_found! == 0 (
    echo [-] 后端服务未运行
)

echo.

REM 停止前端服务(端口 3000)
echo [2/2] 检查前端服务(端口 3000)...
set "frontend_found=0"

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    set "frontend_pid=%%a"
    set "frontend_found=1"
    echo [√] 发现前端服务(PID: %%a)

    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo [!] 无法终止进程 %%a,可能需要管理员权限
    ) else (
        echo [√] 前端服务已停止
    )
)

if !frontend_found! == 0 (
    echo [-] 前端服务未运行
)

echo.
echo ========================================
echo   服务停止完成!
echo ========================================
echo.

REM 等待进程完全终止
echo 等待进程完全终止...
timeout /t 2 /nobreak >nul

REM 再次检查
echo.
echo 最终状态检查:
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [!] 后端服务仍在运行(PID: %%a)
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    echo [!] 前端服务仍在运行(PID: %%a)
)

echo.
echo 如果服务仍在运行,请:
echo   1. 以管理员身份运行此脚本
echo   2. 或手动在服务窗口按 Ctrl+C
echo   3. 或使用任务管理器结束进程
echo.
echo 按任意键退出...
pause >nul

endlocal
