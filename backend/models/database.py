"""
数据库模型定义 - 使用SQLite + SQLAlchemy
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os

# 数据库文件路径
DB_FILE = os.path.join(os.path.dirname(__file__), "../../qmt_web.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite特定配置
    echo=False  # 设置为True可查看SQL日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


class BacktestTask(Base):
    """回测任务表"""
    __tablename__ = "backtest_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    strategy_type = Column(String, nullable=False)  # 'grid' or 'all_weather'
    strategy_config = Column(Text, nullable=True)  # JSON字符串
    backtest_config = Column(Text, nullable=True)  # JSON字符串
    result = Column(Text, nullable=True)  # JSON字符串
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "strategy_type": self.strategy_type,
            "strategy_config": json.loads(self.strategy_config) if self.strategy_config else None,
            "backtest_config": json.loads(self.backtest_config) if self.backtest_config else None,
            "result": json.loads(self.result) if self.result else None,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class OptimizationTask(Base):
    """参数优化任务表"""
    __tablename__ = "optimization_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    strategy_type = Column(String, nullable=False)  # 'grid' or 'all_weather'
    base_config = Column(Text, nullable=True)  # JSON字符串
    optimization_config = Column(Text, nullable=True)  # JSON字符串
    result = Column(Text, nullable=True)  # JSON字符串
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    current_iteration = Column(Integer, default=0)
    total_iterations = Column(Integer, default=0)
    best_result = Column(Text, nullable=True)  # JSON字符串
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "strategy_type": self.strategy_type,
            "base_config": json.loads(self.base_config) if self.base_config else None,
            "optimization_config": json.loads(self.optimization_config) if self.optimization_config else None,
            "result": json.loads(self.result) if self.result else None,
            "status": self.status,
            "current_iteration": self.current_iteration,
            "total_iterations": self.total_iterations,
            "best_result": json.loads(self.best_result) if self.best_result else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class StrategyState(Base):
    """策略状态表（用于实盘监控）"""
    __tablename__ = "strategy_states"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, unique=True, index=True, nullable=False)
    strategy_type = Column(String, nullable=False)  # 'grid' or 'all_weather'
    state = Column(Text, nullable=True)  # JSON字符串 - 策略状态
    status = Column(String, nullable=False)  # 'stopped', 'running', 'error'
    last_update = Column(DateTime, default=datetime.now)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "state": json.loads(self.state) if self.state else None,
            "status": self.status,
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }


# 创建所有表
def init_db():
    """初始化数据库，创建所有表"""
    print(f"初始化数据库: {DB_FILE}")
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成")


# 依赖注入：获取数据库会话
def get_db():
    """获取数据库会话（用于FastAPI依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # 测试数据库初始化
    init_db()
    print("数据库模型测试成功")
