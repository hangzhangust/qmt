# encoding:utf-8
"""
全天候策略核心逻辑模块
从全天候策略.py中提取的框架无关的策略逻辑
"""
import datetime
from typing import Dict, List, Any
from .base_strategy import BaseStrategy


class AllWeatherStrategy(BaseStrategy):
    """
    全天候资产配置策略

    基于25%商品、25%股票、25%长债、25%短债的资产配置
    """

    # 全天候资产配置
    ALL_WEATHER_CONFIG = {
        # 商品类 (25%)
        'commodities': {
            'target_weight': 0.25,
            'etfs': [
                "518880.SH",  # 黄金ETF
                "162411.SH",  # 原油LOF
                "159985.SH",  # 豆粕ETF
            ],
            'names': {
                "518880.SH": "黄金ETF",
                "162411.SH": "原油LOF",
                "159985.SH": "豆粕ETF"
            }
        },
        # 股票类 (25%)
        'stocks': {
            'target_weight': 0.25,
            'etfs': [
                "159915.SZ",  # 沪深300ETF (2012年上市)
                "513100.SH",  # 纳斯达克指数ETF
                "513520.SH",  # 标普500
            ],
            'names': {
                "159915.SZ": "创业板50ETF",
                "513100.SH": "纳斯达克指数ETF",
                "513520.SH": "日经ETF"
            }
        },
        # 长债类 (25%)
        'long_bonds': {
            'target_weight': 0.25,
            'etfs': [
                "511260.SH",  # 国债ETF (2013年上市)
                "511010.SH",  # 长债
            ],
            'names': {
                "511260.SH": "国债ETF",
                "511010.SH": "长债"
            }
        },
        # 短债类 (25%)
        'short_bonds': {
            'target_weight': 0.25,
            'etfs': [
                "511360.SH",  # 短债ETF
            ],
            'names': {
                "511360.SH": "短债ETF"
            }
        }
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化全天候策略

        参数:
            config: 策略配置字典
                - position_ratio: 仓位比例 (默认0.5)
                - rebalance_period: 再平衡周期(天) (默认60)
                - rebalance_threshold: 再平衡阈值 (默认0.05)
        """
        self.position_ratio = config.get('all_weather_position_ratio', 0.5)
        self.rebalance_period = config.get('rebalance_period', 60)
        self.rebalance_threshold = config.get('rebalance_threshold', 0.05)

        # 状态变量
        self.last_rebalance = None
        self.days_since_rebalance = 0
        self.holdings = {}

    def calculate_targets(self, total_value: float) -> Dict[str, float]:
        """
        计算全天候策略各ETF的目标价值

        参数:
            total_value: 总资产价值

        返回:
            dict: {etf_code: target_value}
        """
        target_allocations = {}
        target_value = total_value * self.position_ratio

        for category_name, category_config in self.ALL_WEATHER_CONFIG.items():
            category_weight = category_config['target_weight']
            category_target = target_value * category_weight

            # 每个类别内的ETF等权配置
            etfs_in_category = category_config['etfs']
            etf_count = len(etfs_in_category)

            for etf in etfs_in_category:
                etf_target = category_target / etf_count
                target_allocations[etf] = etf_target

        return target_allocations

    def check_rebalance_condition(self, current_date: str) -> bool:
        """
        检查是否需要再平衡

        参数:
            current_date: 当前日期 (格式: YYYYMMDD)

        返回:
            bool: 是否需要再平衡
        """
        # 如果是第一次运行，需要再平衡
        if self.last_rebalance is None:
            return True

        # 计算距离上次再平衡的天数
        try:
            last_date = datetime.datetime.strptime(self.last_rebalance, '%Y%m%d')
            current_date_obj = datetime.datetime.strptime(current_date, '%Y%m%d')
            days_diff = (current_date_obj - last_date).days

            self.days_since_rebalance = days_diff

            # 如果超过再平衡周期，需要再平衡
            if days_diff >= self.rebalance_period:
                return True

        except Exception as e:
            print(f"计算再平衡周期失败: {e}")

        return False

    def get_configuration(self) -> Dict[str, Any]:
        """
        获取策略配置

        返回:
            dict: 策略配置信息
        """
        return {
            'all_weather_config': self.ALL_WEATHER_CONFIG,
            'position_ratio': self.position_ratio,
            'rebalance_period': self.rebalance_period,
            'rebalance_threshold': self.rebalance_threshold
        }

    def get_etf_universe(self) -> List[str]:
        """
        获取策略涉及的所有ETF代码

        返回:
            list: ETF代码列表
        """
        all_etfs = []
        for category in self.ALL_WEATHER_CONFIG.values():
            all_etfs.extend(category['etfs'])
        return all_etfs

    def get_etf_name(self, etf_code: str) -> str:
        """
        获取ETF名称

        参数:
            etf_code: ETF代码

        返回:
            str: ETF名称
        """
        for category in self.ALL_WEATHER_CONFIG.values():
            if etf_code in category['names']:
                return category['names'][etf_code]
        return "未知"

    def get_category_weights(self) -> Dict[str, float]:
        """
        获取各资产类别的目标权重

        返回:
            dict: {类别名称: 权重}
        """
        return {
            category_name: category_config['target_weight']
            for category_name, category_config in self.ALL_WEATHER_CONFIG.items()
        }

    def get_etf_weights(self) -> Dict[str, float]:
        """
        获取各ETF的等权权重（在给定仓位比例下）

        返回:
            dict: {etf_code: weight}
        """
        weights = {}
        for category_config in self.ALL_WEATHER_CONFIG.values():
            category_weight = category_config['target_weight'] * self.position_ratio
            etfs_in_category = category_config['etfs']
            etf_count = len(etfs_in_category)

            for etf in etfs_in_category:
                weights[etf] = category_weight / etf_count

        return weights

    def get_state(self) -> Dict[str, Any]:
        """
        获取当前策略状态

        返回:
            dict: 策略状态信息
        """
        return {
            'last_rebalance': self.last_rebalance,
            'holdings': self.holdings,
            'days_since_rebalance': self.days_since_rebalance,
            'position_ratio': self.position_ratio,
            'rebalance_period': self.rebalance_period
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        恢复策略状态

        参数:
            state: 策略状态信息
        """
        self.last_rebalance = state.get('last_rebalance')
        self.holdings = state.get('holdings', {})
        self.days_since_rebalance = state.get('days_since_rebalance', 0)

    def update_rebalance_time(self, current_date: str = None) -> None:
        """
        更新再平衡时间

        参数:
            current_date: 当前日期，如果为None则使用当前时间
        """
        if current_date is None:
            current_date = datetime.datetime.now().strftime('%Y%m%d')
        self.last_rebalance = current_date
        self.days_since_rebalance = 0
