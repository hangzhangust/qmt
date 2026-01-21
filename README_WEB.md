# QMT量化交易系统 - Web前端

## 项目概述

为QMT量化交易系统开发的Web前端界面，支持策略回测、参数优化和实盘监控三大核心功能。

## 技术栈

### 后端
- FastAPI: 现代异步Python Web框架
- SQLite + SQLAlchemy: 本地数据持久化
- WebSocket: 实时进度推送

### 前端
- Vue 3: 前端框架
- Vite: 构建工具
- Element Plus: UI组件库
- ECharts: 数据可视化
- Axios: HTTP客户端

## 快速开始

### 1. 安装后端依赖

```bash
pip install -r requirements_web.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 启动后端服务

```bash
cd backend
python main.py
```

后端服务将在 http://127.0.0.1:8000 启动

API文档地址: http://127.0.0.1:8000/docs

### 4. 启动前端服务（开发模式）

```bash
cd frontend
npm run dev
```

前端服务将在 http://localhost:3000 启动

## 项目结构

```
backend/
├── main.py                      # FastAPI应用入口
├── api/                         # API路由（待实现）
├── services/                    # 业务逻辑层（待实现）
├── tasks/
│   └── task_manager.py         # 任务和WebSocket管理
└── models/
    └── database.py             # SQLAlchemy数据库模型

frontend/
├── index.html                   # HTML入口
├── package.json                 # npm配置
├── vite.config.js              # Vite配置
└── src/
    ├── main.js                  # Vue应用入口
    ├── App.vue                  # 根组件
    ├── router/                  # 路由配置
    ├── api/                     # API客户端
    ├── views/                   # 页面组件
    └── components/             # 子组件（待实现）
```

## 开发状态

### ✅ 已完成（阶段1：基础框架）

- [x] 项目目录结构
- [x] FastAPI应用入口
- [x] SQLite数据库模型
- [x] 任务管理器（内存队列）
- [x] Vue 3 + Vite前端框架
- [x] 路由配置
- [x] 基础布局（导航栏）

### 🚧 进行中（阶段2：策略回测功能）

- [ ] 回测API接口
- [ ] 回测服务层
- [ ] 集成现有回测引擎
- [ ] WebSocket进度推送
- [ ] 回测页面完整实现
- [ ] 网格配置表单组件
- [ ] ECharts结果可视化

### 📋 计划中（阶段3-5）

- [ ] 参数优化功能
- [ ] 实盘监控功能
- [ ] 高级优化算法
- [ ] 性能优化和用户体验提升

## 功能特性

### 策略回测
- 支持全天候策略和网格交易策略
- 可调整网格参数（基准价、网格间距、买卖数量）
- 实时显示回测进度
- 完整的结果展示和导出

### 参数优化
- 历史数据回测优化（网格搜索）
- 基于波动率的实时参数推荐
- 可视化分析（热力图、3D曲面图）

### 实盘监控
- 实时账户状态
- 策略运行监控
- WebSocket自动刷新

## 注意事项

1. **XtQuant依赖**: 回测功能需要XtQuant服务运行
2. **数据库**: 首次运行会自动创建SQLite数据库文件
3. **任务队列**: 当前使用内存队列，重启后任务状态会丢失
4. **CORS配置**: 开发环境已配置允许跨域

## 贡献指南

开发时请遵循以下规范：

1. 后端使用类型提示
2. 前端使用Vue 3 Composition API
3. 提交前进行代码测试
4. 更新相关文档

## 许可证

MIT License
