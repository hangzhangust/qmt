"""
任务管理器 - 管理长时间运行的任务和WebSocket连接
"""
from fastapi import WebSocket
from datetime import datetime
from typing import Dict, Optional
import asyncio
import json


class TaskManager:
    """任务管理器 - 使用内存存储任务状态和WebSocket连接"""

    def __init__(self):
        # 任务存储: {task_id: task_info}
        self.tasks: Dict[str, dict] = {}

        # WebSocket连接存储: {task_id: websocket}
        self.websocket_connections: Dict[str, WebSocket] = {}

    def create_task(self, task_id: str, task_type: str, config: dict) -> dict:
        """
        创建新任务

        Args:
            task_id: 任务ID
            task_type: 任务类型 ('backtest', 'optimization')
            config: 任务配置

        Returns:
            任务信息字典
        """
        self.tasks[task_id] = {
            'task_id': task_id,
            'task_type': task_type,
            'status': 'pending',
            'progress': 0,
            'message': '',
            'config': config,
            'result': None,
            'error': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        return self.tasks[task_id]

    def get_task(self, task_id: str) -> Optional[dict]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: str,
                          progress: Optional[int] = None,
                          message: Optional[str] = None,
                          result: Optional[dict] = None,
                          error: Optional[str] = None):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 状态 ('pending', 'running', 'completed', 'failed')
            progress: 进度 (0-100)
            message: 状态消息
            result: 任务结果
            error: 错误信息
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task['status'] = status
        task['updated_at'] = datetime.now().isoformat()

        if progress is not None:
            task['progress'] = progress
        if message is not None:
            task['message'] = message
        if result is not None:
            task['result'] = result
        if error is not None:
            task['error'] = error

        # 自动推送更新到WebSocket
        asyncio.create_task(self._broadcast_update(task_id))

        return True

    def add_websocket(self, task_id: str, websocket: WebSocket):
        """添加WebSocket连接"""
        self.websocket_connections[task_id] = websocket
        print(f"[TaskManager] WebSocket连接已添加: {task_id}")

    def remove_websocket(self, task_id: str):
        """移除WebSocket连接"""
        if task_id in self.websocket_connections:
            del self.websocket_connections[task_id]
            print(f"[TaskManager] WebSocket连接已移除: {task_id}")

    async def _broadcast_update(self, task_id: str):
        """
        广播任务更新到WebSocket客户端

        Args:
            task_id: 任务ID
        """
        if task_id not in self.websocket_connections:
            return

        websocket = self.websocket_connections[task_id]
        task = self.tasks.get(task_id)

        if not task:
            return

        try:
            await websocket.send_json({
                "type": "task_update",
                "task_id": task_id,
                "data": task
            })
        except Exception as e:
            print(f"[TaskManager] WebSocket发送失败: {e}")
            # 发送失败则移除连接
            self.remove_websocket(task_id)

    async def send_message(self, task_id: str, message_type: str, data: dict):
        """
        发送自定义消息到WebSocket客户端

        Args:
            task_id: 任务ID
            message_type: 消息类型
            data: 消息数据
        """
        if task_id not in self.websocket_connections:
            return

        websocket = self.websocket_connections[task_id]

        try:
            await websocket.send_json({
                "type": message_type,
                "task_id": task_id,
                "data": data
            })
        except Exception as e:
            print(f"[TaskManager] WebSocket发送失败: {e}")
            self.remove_websocket(task_id)

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        """
        列出所有任务

        Args:
            task_type: 可选，筛选任务类型

        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())

        if task_type:
            tasks = [t for t in tasks if t['task_type'] == task_type]

        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x['created_at'], reverse=True)

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            # 同时移除WebSocket连接
            self.remove_websocket(task_id)
            return True
        return False


# 全局单例
task_manager = TaskManager()


if __name__ == "__main__":
    # 测试任务管理器
    print("测试任务管理器...")

    # 创建测试任务
    task_id = "test_task_001"
    task_manager.create_task(
        task_id=task_id,
        task_type="backtest",
        config={"strategy": "grid", "params": {}}
    )

    print(f"任务已创建: {task_manager.get_task(task_id)}")

    # 更新任务状态
    task_manager.update_task_status(
        task_id=task_id,
        status="running",
        progress=50,
        message="回测进行中..."
    )

    print(f"任务已更新: {task_manager.get_task(task_id)}")

    # 列出所有任务
    print(f"所有任务: {task_manager.list_tasks()}")

    print("任务管理器测试成功")
