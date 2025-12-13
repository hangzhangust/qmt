"""
日志系统
提供统一的日志记录功能，支持不同级别的日志输出和文件轮转
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
from enum import Enum

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class CustomFormatter(logging.Formatter):
    """自定义日志格式化器"""

    def __init__(self):
        super().__init__()

        # 控制台格式 - 简洁明了
        self.console_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )

        # 文件格式 - 详细信息
        self.file_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record):
        # 根据处理器类型选择格式
        if hasattr(record, 'handler_type'):
            if record.handler_type == 'console':
                return self.console_format.format(record)
            elif record.handler_type == 'file':
                return self.file_format.format(record)

        # 默认使用文件格式
        return self.file_format.format(record)

class ContextFilter(logging.Filter):
    """上下文过滤器，添加额外的上下文信息"""

    def filter(self, record):
        # 添加进程ID和线程ID
        record.process_id = os.getpid()
        record.thread_name = record.threadName

        # 添加模块路径信息
        if hasattr(record, 'module'):
            record.module_path = record.module
        else:
            record.module_path = record.name

        return True

class ETFLogger:
    """ETF网格交易专用日志器"""

    _loggers = {}
    _initialized = False

    @classmethod
    def setup_logger(cls,
                    name: str = "ETFGridTrading",
                    log_level: LogLevel = LogLevel.INFO,
                    log_file: Optional[str] = None,
                    console_output: bool = True,
                    max_file_size: int = 10 * 1024 * 1024,  # 10MB
                    backup_count: int = 5) -> logging.Logger:
        """
        设置日志器

        Args:
            name: 日志器名称
            log_level: 日志级别
            log_file: 日志文件路径
            console_output: 是否输出到控制台
            max_file_size: 日志文件最大大小
            backup_count: 备份文件数量
        """

        if name in cls._loggers:
            return cls._loggers[name]

        # 创建日志器
        logger = logging.getLogger(name)
        logger.setLevel(log_level.value)

        # 清除现有处理器
        logger.handlers.clear()

        # 设置格式化器
        formatter = CustomFormatter()
        context_filter = ContextFilter()

        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level.value)
            console_handler.setFormatter(formatter)

            # 为控制台处理器标记类型
            console_handler.addFilter(lambda record: setattr(record, 'handler_type', 'console') or True)
            console_handler.addFilter(context_filter)
            logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            # 使用RotatingFileHandler实现日志轮转
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level.value)
            file_handler.setFormatter(formatter)

            # 为文件处理器标记类型
            file_handler.addFilter(lambda record: setattr(record, 'handler_type', 'file') or True)
            file_handler.addFilter(context_filter)
            logger.addHandler(file_handler)

        # 防止日志传播到根日志器
        logger.propagate = False

        # 缓存日志器
        cls._loggers[name] = logger
        cls._initialized = True

        return logger

    @classmethod
    def get_logger(cls, name: str = "ETFGridTrading") -> logging.Logger:
        """获取日志器"""
        if name not in cls._loggers:
            return cls.setup_logger(name)
        return cls._loggers[name]

    @classmethod
    def set_log_level(cls, level: LogLevel, logger_name: str = "ETFGridTrading"):
        """设置日志级别"""
        logger = cls.get_logger(logger_name)
        logger.setLevel(level.value)

        # 更新所有处理器的级别
        for handler in logger.handlers:
            handler.setLevel(level.value)

class PerformanceLogger:
    """性能监控日志器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_times = {}

    def start_timer(self, operation: str):
        """开始计时"""
        self.start_times[operation] = datetime.now()
        self.logger.debug(f"开始执行: {operation}")

    def end_timer(self, operation: str):
        """结束计时并记录"""
        if operation in self.start_times:
            duration = datetime.now() - self.start_times[operation]
            del self.start_times[operation]

            self.logger.debug(f"完成执行: {operation}, 耗时: {duration.total_seconds():.3f}秒")
            return duration.total_seconds()
        else:
            self.logger.warning(f"未找到操作的开始时间: {operation}")
            return 0

class TradingLogger:
    """交易专用日志器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_order(self, order_type: str, symbol: str, direction: str,
                  quantity: int, price: float, status: str = "SUBMITTED"):
        """记录订单日志"""
        self.logger.info(
            f"订单 {status}: {direction} {symbol} {quantity}股 "
            f"@¥{price:.3f} ({order_type})"
        )

    def log_fill(self, symbol: str, direction: str, quantity: int,
                 price: float, trade_id: str = ""):
        """记录成交日志"""
        self.logger.info(
            f"成交: {direction} {symbol} {quantity}股 "
            f"@¥{price:.3f} (ID: {trade_id})"
        )

    def log_position_change(self, symbol: str, old_quantity: int,
                           new_quantity: int, avg_price: float):
        """记录持仓变化"""
        change = new_quantity - old_quantity
        action = "增加" if change > 0 else "减少" if change < 0 else "不变"

        self.logger.info(
            f"持仓变化: {symbol} {action} {abs(change)}股, "
            f"当前持仓: {new_quantity}股, 成本价: ¥{avg_price:.3f}"
        )

    def log_risk_alert(self, alert_type: str, symbol: str, current_value: float,
                      threshold: float, description: str = ""):
        """记录风险警报"""
        self.logger.warning(
            f"风险警报: {alert_type} - {symbol} "
            f"(当前: {current_value:.3f}, 阈值: {threshold:.3f}) "
            f"{description}"
        )

    def log_strategy_event(self, event_type: str, symbol: str,
                          details: str = ""):
        """记录策略事件"""
        self.logger.info(
            f"策略事件: {event_type} - {symbol} {details}"
        )

def setup_logger(name: str = "ETFGridTrading",
                log_level: LogLevel = LogLevel.INFO,
                log_file: Optional[str] = None,
                console_output: bool = True) -> logging.Logger:
    """便捷的日志器设置函数"""
    return ETFLogger.setup_logger(
        name=name,
        log_level=log_level,
        log_file=log_file,
        console_output=console_output
    )

def get_logger(name: str = "ETFGridTrading") -> logging.Logger:
    """便捷的日志器获取函数"""
    return ETFLogger.get_logger(name)

# 预定义的日志器
main_logger = get_logger("Main")
data_logger = get_logger("Data")
strategy_logger = get_logger("Strategy")
risk_logger = get_logger("Risk")
execution_logger = get_logger("Execution")
backtest_logger = get_logger("Backtest")