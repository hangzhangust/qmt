@echo off
REM QMT 量化交易系统 - 开发环境启动脚本
REM 用于启动前后端开发服务器(带热重载)

chcp 65001 >nul
setlocal enabledelayedexpansion

title QMT 开发环境启动器

echo ========================================
echo   QMT 量化交易系统 - 开发环境
echo ========================================
echo.
echo 正在启动开发环境...
echo.

REM 检查当前目录
if not exist "backend\main.py" (
    echo [错误] 请在项目根目录运行此脚本!
    echo.
    pause
    exit /b 1
)

REM 检查依赖
echo [1/3] 检查依赖...
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

REM 检查后端依赖
echo [2/3] 检查后端依赖...
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

REM 检查前端依赖
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
echo [3/3] 启动服务...
echo.
echo 正在启动后端服务(端口 8000)...
start "QMT Backend - Development" cmd /k "cd backend && python main.py"

REM 等待后端启动
echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

echo.
echo 正在启动前端服务(端口 3000)...
start "QMT Frontend - Development" cmd /k "cd frontend && npm run dev"

REM 等待前端启动
echo 等待前端服务启动...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   开发环境启动完成!
echo ========================================
echo.
echo 服务地址:
echo   - 后端 API: http://127.0.0.1:8000/docs
echo   - 后端健康检查: http://127.0.0.1:8000/health
echo   - 前端界面: http://localhost:3000
echo.
echo 提示:
echo   - 两个服务窗口已打开
echo   - 关闭窗口即可停止对应服务
echo   - 或运行 stop_services.bat 停止所有服务
echo   - 代码修改会自动重载(热重载)
echo.
echo 按任意键检查服务状态...
pause >nul

REM 检查服务状态
powershell -ExecutionPolicy Bypass -File "%~dp0check_services.ps1"

endlocal
