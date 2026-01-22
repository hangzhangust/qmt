# QMT 量化交易系统 - 服务启动指南

本文档提供 QMT 量化交易系统前后端服务的详细启动说明,包括开发和生产两种环境。

## 目录

- [系统架构](#系统架构)
- [环境准备](#环境准备)
- [检查服务状态](#检查服务状态)
- [开发环境启动](#开发环境启动)
- [生产环境启动](#生产环境启动)
- [停止服务](#停止服务)
- [验证服务](#验证服务)
- [常见问题](#常见问题)

---

## 系统架构

QMT 量化交易系统由前端和后端两部分组成:

### 后端服务 (FastAPI)
- **入口文件**: `backend/main.py`
- **运行端口**: 8000
- **访问地址**:
  - API 文档: http://127.0.0.1:8000/docs
  - 健康检查: http://127.0.0.1:8000/health
- **技术栈**: FastAPI + Uvicorn + SQLite
- **依赖文件**: `requirements_web.txt`

### 前端服务 (Vue 3 + Vite)
- **目录**: `frontend/`
- **运行端口**: 3000
- **访问地址**: http://localhost:3000
- **技术栈**: Vue 3 + Vite + Element Plus + ECharts
- **依赖文件**: `frontend/package.json`

### 架构说明
- 前端通过 Vite 代理将 `/api` 请求转发到后端 8000 端口
- 开发模式下前后端独立运行,支持热重载
- 生产模式下前端构建后可由后端静态文件服务提供

---

## 环境准备

### 依赖安装

#### 1. 安装 Python 依赖
```bash
# 在项目根目录执行
pip install -r requirements_web.txt
```

主要依赖包括:
- fastapi >= 0.104.0
- uvicorn[standard] >= 0.24.0
- websockets >= 12.0
- sqlalchemy >= 2.0.0
- aiosqlite >= 0.19.0
- pydantic >= 2.0.0

#### 2. 安装前端依赖
```bash
# 进入前端目录
cd frontend

# 安装 npm 依赖(首次使用)
npm install
```

主要依赖包括:
- vue ^3.3.0
- vue-router ^4.2.0
- element-plus ^2.4.0
- echarts ^5.4.0
- axios ^1.6.0

#### 3. 验证环境
```bash
# 检查 Python 版本(需要 3.8+)
python --version

# 检查 Node.js 版本(需要 16+)
node --version

# 检查 npm 版本
npm --version
```

### PowerShell 执行策略

如果无法运行 PowerShell 脚本(.ps1),需要设置执行策略:

```powershell
# 以管理员身份运行 PowerShell,执行:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 检查服务状态

### 使用脚本检查(推荐)

```powershell
# 在项目根目录运行
.\check_services.ps1
```

该脚本会显示:
- 后端服务状态(端口 8000)
- 前端服务状态(端口 3000)
- 进程信息(PID、进程名)
- 健康检查结果
- 依赖安装情况

### 手动检查端口

```powershell
# 检查端口 8000 是否被占用
netstat -ano | findstr :8000

# 检查端口 3000 是否被占用
netstat -ano | findstr :3000
```

---

## 开发环境启动

开发模式支持热重载,适合开发和调试。

### 方法 1: 使用批处理脚本(推荐)

```bash
# 一键启动前后端服务
.\start_dev.bat
```

脚本会自动:
1. 打开两个命令行窗口
2. 在第一个窗口启动后端服务
3. 在第二个窗口启动前端服务
4. 保持窗口打开以查看日志

### 方法 2: 手动启动

#### 步骤 1: 启动后端服务

打开**第一个命令行窗口**:

```bash
# 进入后端目录
cd backend

# 启动开发服务器(带热重载)
python main.py
```

**预期输出**:
```
============================================================
QMT量化交易系统 Web后端服务启动中...
============================================================
API文档地址: http://127.0.0.1:8000/docs
健康检查: http://127.0.0.1:8000/health
============================================================
初始化数据库...
数据库初始化完成
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

#### 步骤 2: 启动前端服务

打开**第二个命令行窗口**:

```bash
# 进入前端目录
cd frontend

# 启动开发服务器(带热重载)
npm run dev
```

**预期输出**:
```
  VITE v5.0.0  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

### 开发模式特性

- **热重载**: 修改代码后自动重启服务
- **详细日志**: 显示完整的请求和错误信息
- **源码映射**: 支持浏览器调试原始源码
- **CORS 已启用**: 前端可以无限制访问后端 API

---

## 生产环境启动

生产模式优化了性能,不包含开发工具。

### 方法 1: 使用批处理脚本(推荐)

```bash
# 一键启动生产环境
.\start_prod.bat
```

脚本会自动:
1. 构建前端资源(如果需要)
2. 启动后端生产服务器(多进程)
3. 启动前端预览服务

### 方法 2: 手动启动

#### 步骤 1: 构建前端

```bash
# 进入前端目录
cd frontend

# 构建生产版本(首次或代码更新后)
npm run build
```

构建完成后,`frontend/dist/` 目录会包含静态文件。

#### 步骤 2: 启动后端服务

打开**第一个命令行窗口**:

```bash
# 进入后端目录
cd backend

# 使用 uvicorn 启动生产服务器(4个worker进程)
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
```

**生产模式参数说明**:
- `--workers 4`: 启动 4 个工作进程(可根据 CPU 核心数调整)
- `--reload`: 不使用热重载(生产环境不需要)
- `--log-level warning`: 减少日志输出

#### 步骤 3: 预览前端(可选)

打开**第二个命令行窗口**:

```bash
# 进入前端目录
cd frontend

# 预览构建后的前端
npm run preview
```

或者将 `frontend/dist/` 目录配置到 Nginx 等Web服务器。

### 生产模式特性

- **性能优化**: 代码压缩、Tree-shaking、资源哈希
- **多进程**: 后端启动多个 worker 提高并发处理能力
- **静态文件**: 可直接由 Web 服务器提供,无需 Node.js
- **减少日志**: 只输出必要的警告和错误信息

---

## 停止服务

### 方法 1: 使用批处理脚本(推荐)

```bash
# 停止前后端所有服务
.\stop_services.bat
```

### 方法 2: 手动停止

#### 在命令行窗口中停止

在各个服务窗口中按 `Ctrl + C` 停止服务。

#### 强制终止进程

```powershell
# 查找并终止占用端口 8000 的进程
netstat -ano | findstr :8000
taskkill /F /PID <进程ID>

# 查找并终止占用端口 3000 的进程
netstat -ano | findstr :3000
taskkill /F /PID <进程ID>
```

---

## 验证服务

### 1. 后端验证

#### 健康检查
```bash
# 在浏览器或命令行访问
http://127.0.0.1:8000/health
```

**预期响应**:
```json
{"status": "healthy"}
```

#### API 文档
访问 http://127.0.0.1:8000/docs 查看 Swagger UI 文档。

#### 测试 API
```bash
# 测试根路径
curl http://127.0.0.1:8000/

# 预期响应
{
  "message": "QMT量化交易系统 Web API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

### 2. 前端验证

#### 访问前端
在浏览器打开 http://localhost:3000

**预期结果**:
- 看到 QMT 量化交易系统的主界面
- 显示三个主要功能模块:策略回测、参数优化、实盘监控
- 浏览器控制台(F12)无错误信息

#### 检查网络请求
1. 打开浏览器开发者工具(F12)
2. 切换到 Network 标签
3. 执行前端操作(如配置网格交易参数)
4. 检查 API 请求是否成功:
   - 请求地址应为: `http://127.0.0.1:8000/api/...`
   - 状态码应为: 200、201 等
   - 响应数据格式正确

### 3. 前后端通信验证

1. 在前端界面配置网格交易策略
2. 提交回测任务
3. 观察前端是否显示任务提交成功
4. 检查后端日志是否显示接收到请求
5. 验证 WebSocket 连接是否正常(如果有实时更新功能)

---

## 常见问题

### 端口被占用

**问题**: 启动时提示 `Address already in use` 或端口已被使用

**解决方案**:

1. 查找占用端口的进程:
```powershell
netstat -ano | findstr :8000
```

2. 终止该进程:
```powershell
taskkill /F /PID <进程ID>
```

3. 或者修改服务使用的端口:
   - 后端: 修改 `backend/main.py` 中的 `port=8000`
   - 前端: 修改 `frontend/vite.config.js` 中的 `port: 3000`

### 依赖安装失败

**问题**: `pip install` 或 `npm install` 失败

**解决方案**:

**Python 依赖**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements_web.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**npm 依赖**:
```bash
# 清除 npm 缓存
npm cache clean --force

# 使用国内镜像源
npm config set registry https://registry.npmmirror.com
npm install
```

### CORS 错误

**问题**: 前端无法访问后端 API,浏览器显示 CORS 错误

**解决方案**:

开发环境 CORS 已在 `backend/main.py` 中配置为允许所有源:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

如果仍有问题:
1. 确认后端服务正在运行
2. 检查前端代理配置(`frontend/vite.config.js`)
3. 确认前端访问的地址正确

### 数据库错误

**问题**: 启动后端时提示数据库相关错误

**解决方案**:

1. SQLite 数据库会在首次启动时自动创建
2. 确保有文件写入权限
3. 检查 `backend/models/database.py` 中的数据库路径
4. 删除损坏的数据库文件(如果存在),让服务重新创建

### 前端空白页

**问题**: 访问 http://localhost:3000 显示空白页

**解决方案**:

1. 检查前端服务是否正常运行
2. 打开浏览器控制台查看错误信息
3. 确认 `npm install` 已执行
4. 尝试清除浏览器缓存
5. 重启前端服务(`Ctrl + C` 后重新 `npm run dev`)

### WebSocket 连接失败

**问题**: 前端无法建立 WebSocket 连接

**解决方案**:

1. 确认后端 WebSocket 端点配置正确
2. 检查前端 WebSocket 连接地址
3. 确认防火墙未阻止 WebSocket 连接
4. 查看浏览器控制台的 WebSocket 相关错误

### 服务自动重启

**问题**: 开发模式下服务频繁重启

**解决方案**:

这是正常的热重载行为。如需禁用:

**后端**: 修改 `backend/main.py`:
```python
uvicorn.run(
    app,
    host="127.0.0.1",
    port=8000,
    reload=False,  # 改为 False
    log_level="info"
)
```

**前端**: 使用生产构建:
```bash
npm run build
npm run preview
```

---

## 快速参考

### 开发环境快速启动

```bash
# 方式 1: 一键启动
.\start_dev.bat

# 方式 2: 分步启动
# 终端 1
cd backend && python main.py

# 终端 2
cd frontend && npm run dev
```

### 生产环境快速启动

```bash
# 方式 1: 一键启动
.\start_prod.bat

# 方式 2: 分步启动
# 终端 1 - 后端
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4

# 终端 2 - 前端构建和预览
cd frontend
npm run build
npm run preview
```

### 快速停止

```bash
# 使用停止脚本
.\stop_services.bat

# 或在各个窗口按 Ctrl+C
```

### 检查状态

```bash
.\check_services.ps1
```

---

## 附录

### 技术支持

如遇到问题,请检查:
1. 本指南的[常见问题](#常见问题)章节
2. 项目 README 文档
3. 后端 API 文档: http://127.0.0.1:8000/docs
4. 浏览器控制台的错误信息
5. 后端服务的日志输出

### 相关文档

- `README_WEB.md` - Web 应用整体说明
- `IMPLEMENTATION_SUMMARY.md` - 实现总结
- `BACKTEST_GUIDE.md` - 回测系统使用指南

### 更新日志

- **v1.0.0** (2024) - 初始版本,支持前后端服务管理

---

**祝使用愉快!** 🚀
