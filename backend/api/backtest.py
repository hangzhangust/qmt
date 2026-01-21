"""
回测API路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import json
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backtest_service import BacktestService
from tasks.task_manager import task_manager
from models.database import BacktestTask, get_db

# 创建路由器
router = APIRouter()

# ==================== 请求/响应模型 ====================

class GridStrategyConfig(BaseModel):
    """网格策略配置"""
    etf_code: str = Field(..., description="ETF代码")
    etf_name: Optional[str] = Field(None, description="ETF名称")
    base_price: float = Field(..., gt=0, description="基准价格")
    grid_spacing_up: float = Field(..., gt=0, le=100, description="上涨网格间距(%)")
    grid_spacing_down: float = Field(..., lt=0, ge=-100, description="下跌网格间距(%)")
    buy_amount: float = Field(..., gt=0, description="买入数量")
    sell_amount: float = Field(..., gt=0, description="卖出数量")
    buy_amount_type: str = Field("shares", description="买入数量类型: shares/currency")
    sell_amount_type: str = Field("shares", description="卖出数量类型: shares/currency")


class BacktestConfig(BaseModel):
    """回测配置"""
    start_date: str = Field(..., description="开始日期 (YYYYMMDD)")
    end_date: str = Field(..., description="结束日期 (YYYYMMDD)")
    initial_cash: float = Field(1000000, gt=0, description="初始资金")


class RunBacktestRequest(BaseModel):
    """运行回测请求"""
    strategy_type: str = Field("grid", description="策略类型: grid/all_weather")
    strategy_config: Dict[str, Any] = Field(..., description="策略配置")
    backtest_config: BacktestConfig = Field(..., description="回测配置")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str


# ==================== API接口 ====================

@router.post("/run", response_model=TaskResponse)
async def run_backtest(request: RunBacktestRequest):
    """
    启动回测任务

    Args:
        request: 回测请求

    Returns:
        TaskResponse: 任务ID和状态
    """
    try:
        # 生成任务ID
        task_id = BacktestService.generate_task_id()

        # 验证网格策略配置
        if request.strategy_type == 'grid':
            is_valid, error_msg = BacktestService.validate_grid_config(request.strategy_config)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"配置验证失败: {error_msg}")

        # 创建任务记录
        task_manager.create_task(
            task_id=task_id,
            task_type='backtest',
            config={
                'strategy_type': request.strategy_type,
                'strategy_config': request.strategy_config,
                'backtest_config': request.backtest_config.dict(),
            }
        )

        # 更新任务状态为运行中
        task_manager.update_task_status(
            task_id=task_id,
            status='running',
            progress=0,
            message="回测任务已启动"
        )

        # 异步执行回测
        async def run_backtest_async():
            try:
                # 定义进度回调
                async def progress_callback(progress: int, message: str):
                    task_manager.update_task_status(
                        task_id=task_id,
                        status='running',
                        progress=progress,
                        message=message
                    )

                # 运行回测
                result = await BacktestService.run_backtest(
                    task_id=task_id,
                    strategy_type=request.strategy_type,
                    strategy_config=request.strategy_config,
                    backtest_config=request.backtest_config.dict(),
                    progress_callback=progress_callback
                )

                # 检查是否出错
                if 'error' in result:
                    task_manager.update_task_status(
                        task_id=task_id,
                        status='failed',
                        progress=100,
                        error=result['error']
                    )
                else:
                    # 回测成功
                    task_manager.update_task_status(
                        task_id=task_id,
                        status='completed',
                        progress=100,
                        message="回测完成",
                        result=result
                    )

            except Exception as e:
                import traceback
                error_msg = f"回测执行异常: {str(e)}\n{traceback.format_exc()}"
                task_manager.update_task_status(
                    task_id=task_id,
                    status='failed',
                    progress=0,
                    error=error_msg
                )

        # 启动后台任务
        import asyncio
        asyncio.create_task(run_backtest_async())

        return TaskResponse(
            task_id=task_id,
            status="running",
            message="回测任务已启动"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"启动回测失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/tasks/{task_id}")
async def get_backtest_task(task_id: str):
    """
    查询回测任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务信息
    """
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return task


@router.get("/tasks")
async def list_backtest_tasks():
    """
    列出所有回测任务

    Returns:
        任务列表
    """
    tasks = task_manager.list_tasks(task_type='backtest')
    return {"tasks": tasks}


@router.delete("/tasks/{task_id}")
async def delete_backtest_task(task_id: str):
    """
    删除回测任务

    Args:
        task_id: 任务ID

    Returns:
        删除结果
    """
    success = task_manager.delete_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return {"message": "任务已删除", "task_id": task_id}


# ==================== WebSocket接口 ====================

@router.websocket("/ws/{task_id}")
async def backtest_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket连接 - 实时接收回测进度

    Args:
        websocket: WebSocket连接
        task_id: 任务ID
    """
    await websocket.accept()

    # 添加WebSocket连接
    task_manager.add_websocket(task_id, websocket)

    try:
        # 发送连接确认消息
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "WebSocket连接成功"
        })

        # 发送当前任务状态
        task = task_manager.get_task(task_id)
        if task:
            await websocket.send_json({
                "type": "task_update",
                "task_id": task_id,
                "data": task
            })

        # 保持连接，接收客户端消息
        while True:
            data = await websocket.receive_text()
            # 可以处理客户端发送的消息（如取消任务等）
            print(f"[WebSocket] Received from {task_id}: {data}")

    except WebSocketDisconnect:
        print(f"[WebSocket] Disconnected: {task_id}")
        task_manager.remove_websocket(task_id)
    except Exception as e:
        print(f"[WebSocket] Error for {task_id}: {e}")
        task_manager.remove_websocket(task_id)


# ==================== 工具函数 ====================

def format_result_for_display(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    格式化回测结果用于前端显示

    Args:
        result: 原始回测结果

    Returns:
        格式化后的结果
    """
    # 提取关键指标
    display_result = {
        'etf_code': result.get('etf_code', ''),
        'etf_name': result.get('etf_name', ''),
        'final_value': result.get('final_value', 0),
        'total_return': result.get('total_return', 0),
        'total_pnl': result.get('total_pnl', 0),
        'sharpe_ratio': result.get('sharpe_ratio', 0),
        'max_drawdown': result.get('max_drawdown', 0),
        'total_grid_triggers': result.get('total_grid_triggers', 0),
        'buy_triggers': result.get('buy_triggers', 0),
        'sell_triggers': result.get('sell_triggers', 0),
        'grid_triggers': result.get('grid_triggers', []),
        'performance_summary': result.get('performance_summary', {}),
    }

    return display_result


if __name__ == "__main__":
    # 测试API
    print("回测API路由模块")
    print("使用 uvicorn main:app 启动服务器")
