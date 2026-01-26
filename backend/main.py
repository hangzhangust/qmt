"""
QMT量化交易系统 - Web后端应用入口
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

# 导入API路由
from api import backtest, market_data

# 导入数据库模型
from models.database import init_db

# 创建FastAPI应用实例
app = FastAPI(
    title="QMT量化交易系统",
    description="支持策略回测、参数优化和实盘监控的量化交易Web平台",
    version="1.0.0"
)

# 配置CORS - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测"])
app.include_router(market_data.router, prefix="/api/market", tags=["市场数据"])
# app.include_router(monitor.router, prefix="/api/monitor", tags=["监控"])
# app.include_router(optimization.router, prefix="/api/optimization", tags=["优化"])


# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    print("初始化数据库...")
    init_db()
    print("数据库初始化完成")


# 健康检查接口
@app.get("/")
async def root():
    """根路径 - 欢迎页面"""
    return {
        "message": "QMT量化交易系统 Web API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}

# WebSocket连接管理（示例，后续在task_manager中实现）
@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """WebSocket测试接口"""
    await websocket.accept()
    await websocket.send_json({"message": "WebSocket连接成功"})
    await websocket.close()

# 静态文件服务（生产模式下提供前端构建产物）
if os.path.exists("backend/static"):
    app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# 主程序入口
if __name__ == "__main__":
    print("=" * 60)
    print("QMT量化交易系统 Web后端服务启动中...")
    print("=" * 60)
    print("API文档地址: http://127.0.0.1:8000/docs")
    print("健康检查: http://127.0.0.1:8000/health")
    print("=" * 60)

    uvicorn.run(
        "main:app",  # 使用字符串格式导入应用以支持reload
        host="127.0.0.1",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )
