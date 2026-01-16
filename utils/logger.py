# -*- coding: utf-8 -*-
"""
Logger Module
Unified logging management system
"""
import logging
import os
from datetime import datetime
from typing import Optional


class StrategyLogger:
    """
    策略日志系统
    提供统一的日志接口，支持控制台和文件输出
    """

    # 日志级别映射
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    def __init__(self, name: str = 'StrategyLogger',
                 log_dir: Optional[str] = None,
                 log_level: str = 'INFO',
                 console_output: bool = True,
                 file_output: bool = True):
        """
        初始化日志系统

        参数:
            name: 日志器名称
            log_dir: 日志文件目录（默认为 ~/QMT_Strategy_Data/logs）
            log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
        """
        self.name = name
        self.log_dir = log_dir
        self.log_level = self.LOG_LEVELS.get(log_level.upper(), logging.INFO)
        self.console_output = console_output
        self.file_output = file_output

        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)

        # 清除已有的处理器
        self.logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 添加控制台处理器
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # 添加文件处理器
        if file_output:
            # 设置日志目录
            if not self.log_dir:
                home_dir = os.path.expanduser('~')
                self.log_dir = os.path.join(home_dir, 'QMT_Strategy_Data', 'logs')

            # 创建日志目录
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

            # 日志文件路径
            log_file = self._get_log_file_path()

            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        print(f"[{name}] 日志系统初始化完成")
        print(f"  日志级别: {log_level}")
        print(f"  控制台输出: {'是' if console_output else '否'}")
        print(f"  文件输出: {'是' if file_output else '否'}")
        if file_output:
            print(f"  日志目录: {self.log_dir}")

    def _get_log_file_path(self) -> str:
        """
        获取日志文件路径

        返回:
            str: 日志文件路径
        """
        # 使用日期作为日志文件名
        date_str = datetime.now().strftime('%Y%m%d')
        log_file_name = f'strategy_{date_str}.log'
        log_file_path = os.path.join(self.log_dir, log_file_name)

        return log_file_path

    def debug(self, message: str) -> None:
        """
        记录DEBUG级别日志

        参数:
            message: 日志消息
        """
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """
        记录INFO级别日志

        参数:
            message: 日志消息
        """
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """
        记录WARNING级别日志

        参数:
            message: 日志消息
        """
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """
        记录ERROR级别日志

        参数:
            message: 日志消息
        """
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """
        记录CRITICAL级别日志

        参数:
            message: 日志消息
        """
        self.logger.critical(message)

    def trade(self, stock_code: str, action: str, volume: int,
              price: float, amount: float) -> None:
        """
        记录交易日志（专门用于记录交易）

        参数:
            stock_code: 股票代码
            action: 操作类型（buy/sell）
            volume: 成交数量
            price: 成交价格
            amount: 成交金额
        """
        action_str = '买入' if action == 'buy' else '卖出'
        message = f"交易 - {action_str} {stock_code}: {volume}股 @ {price:.2f}元, 金额{amount:.2f}元"
        self.logger.info(message)

    def rebalance(self, total_assets: float, target_value: float,
                  holdings_count: int) -> None:
        """
        记录再平衡日志

        参数:
            total_assets: 总资产
            target_value: 目标投资金额
            holdings_count: 持仓数量
        """
        message = f"再平衡 - 总资产: {total_assets:.2f}元, 目标投资: {target_value:.2f}元, 持仓数: {holdings_count}"
        self.logger.info(message)

    def error_with_traceback(self, message: str, exc_info: bool = True) -> None:
        """
        记录错误日志（包含异常信息）

        参数:
            message: 错误消息
            exc_info: 是否包含异常堆栈
        """
        self.logger.error(message, exc_info=exc_info)


# 全局日志器实例（默认）
_global_logger = None


def get_logger(name: str = 'StrategyLogger',
               log_dir: Optional[str] = None,
               log_level: str = 'INFO',
               console_output: bool = True,
               file_output: bool = True) -> StrategyLogger:
    """
    获取日志器实例（单例模式）

    参数:
        name: 日志器名称
        log_dir: 日志文件目录
        log_level: 日志级别
        console_output: 是否输出到控制台
        file_output: 是否输出到文件

    返回:
        StrategyLogger: 日志器实例
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = StrategyLogger(
            name=name,
            log_dir=log_dir,
            log_level=log_level,
            console_output=console_output,
            file_output=file_output
        )

    return _global_logger


# 测试代码
if __name__ == '__main__':
    # 测试日志系统
    print("=" * 60)
    print("日志系统测试")
    print("=" * 60)

    # 创建日志器
    logger = StrategyLogger(
        name='TestLogger',
        log_level='DEBUG',
        console_output=True,
        file_output=True
    )

    # 测试各级别日志
    print("\n--- 测试各级别日志 ---")
    logger.debug("这是DEBUG级别日志")
    logger.info("这是INFO级别日志")
    logger.warning("这是WARNING级别日志")
    logger.error("这是ERROR级别日志")

    # 测试交易日志
    print("\n--- 测试交易日志 ---")
    logger.trade('000001.SZ', 'buy', 100, 5.5, 550)

    # 测试再平衡日志
    print("\n--- 测试再平衡日志 ---")
    logger.rebalance(1000000, 500000, 10)

    # 测试异常日志
    print("\n--- 测试异常日志 ---")
    try:
        1 / 0
    except Exception as e:
        logger.error_with_traceback(f"发生异常: {e}")

    print("\n✓ 日志测试完成")
    print(f"日志文件位置: {logger.log_dir}")
