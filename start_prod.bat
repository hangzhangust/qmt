@echo off
REM QMT 量化交易系统 - 生产环境启动脚本
REM 用于启动前后端生产服务器(优化性能)

chcp 65001 >nul
setlocal enabledelayedexpansion

title QMT 生产环境启动器

echo ========================================
echo   QMT 量化交易系统 - 生产环境
echo ========================================
echo.
echo 正在启动生产环境...
echo.

REM 检查当前目录
if not exist "backend\main.py" (
    echo [错误] 请在项目根目录运行此脚本!
    echo.
    pause
    exit /b 1
)

REM 检查依赖
echo [1/4] 检查依赖...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未安装或不在 PATH 中
    echo 请先安装 Python 3.8+
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Node.js 未安装或不在 PATH 中
    echo 请先安装 Node.js 16+
    pause
    exit /b 1
)

echo [√] 依赖检查通过
echo.

REM 检查并安装后端依赖
echo [2/4] 检查后端依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [提示] 后端依赖未安装,正在安装...
    pip install -r requirements_web.txt
    if errorlevel 1 (
        echo [错误] 后端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [√] 后端依赖已安装
)

REM 检查并安装前端依赖
if not exist "frontend\node_modules\" (
    echo [提示] 前端依赖未安装,正在安装...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [√] 前端依赖安装完成
) else (
    echo [√] 前端依赖已安装
)

echo.

REM 构建前端
echo [3/4] 构建前端生产版本...
if not exist "frontend\dist\" (
    echo [提示] 前端未构建,正在构建...
    cd frontend
    call npm run build
    if errorlevel 1 (
        echo [错误] 前端构建失败
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [√] 前端构建完成
) else (
    echo [√] 前端已构建(如需重新构建,请删除 frontend\dist 目录)
)

echo.
echo [4/4] 启动服务...
echo.
echo 正在启动后端服务(端口 8000, 4个worker进程)...
start "QMT Backend - Production" cmd /k "cd backend && uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4 --log-level warning"

REM 等待后端启动
echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

echo.
echo 正在启动前端预览服务(端口 3000)...
start "QMT Frontend - Production Preview" cmd /k "cd frontend && npm run preview"

REM 等待前端启动
echo 等待前端服务启动...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   生产环境启动完成!
echo ========================================
echo.
echo 服务地址:
echo   - 后端 API: http://127.0.0.1:8000/docs
echo   - 后端健康检查: http://127.0.0.1:8000/health
echo   - 前端界面: http://localhost:3000
echo.
echo 生产模式特性:
echo   - 后端使用 4 个 worker 进程(提高并发性能)
echo   - 前端已构建并优化(代码压缩、Tree-shaking)
echo   - 禁用热重载(减少资源占用)
echo   - 减少日志输出(只显示警告和错误)
echo.
echo 提示:
echo   - 两个服务窗口已打开
echo   - 关闭窗口即可停止对应服务
echo   - 或运行 stop_services.bat 停止所有服务
echo   - 生产环境不支持热重载,修改代码需重新构建和启动
echo.
echo 按任意键检查服务状态...
pause >nul

REM 检查服务状态
powershell -ExecutionPolicy Bypass -File "%~dp0check_services.ps1"

endlocal
