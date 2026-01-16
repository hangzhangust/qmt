# encoding:utf-8
"""
策略基类模块
定义所有策略的抽象接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseStrategy(ABC):
    """
    策略抽象基类
    所有交易策略都应继承此类并实现核心方法
    """

    @abstractmethod
    def calculate_targets(self, total_value: float) -> Dict[str, float]:
        """
        计算目标配置

        参数:
            total_value: 总资产价值

        返回:
            dict: {资产代码: 目标价值}
        """
        pass

    @abstractmethod
    def check_rebalance_condition(self, current_date: str) -> bool:
        """
        检查是否需要再平衡

        参数:
            current_date: 当前日期 (格式: YYYYMMDD)

        返回:
            bool: 是否需要再平衡
        """
        pass

    @abstractmethod
    def get_configuration(self) -> Dict[str, Any]:
        """
        获取策略配置

        返回:
            dict: 策略配置信息
        """
        pass

    @abstractmethod
    def get_etf_universe(self) -> List[str]:
        """
        获取策略涉及的所有ETF代码

        返回:
            list: ETF代码列表
        """
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        获取当前策略状态

        返回:
            dict: 策略状态信息
        """
        pass

    @abstractmethod
    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        恢复策略状态

        参数:
            state: 策略状态信息
        """
        pass
