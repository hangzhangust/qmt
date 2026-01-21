# encoding:utf-8
"""
网格交易策略核心模块
定义网格交易策略的核心逻辑
"""
from typing import Dict, Any, List
from strategies.base_strategy import BaseStrategy


class GridStrategy(BaseStrategy):
    """
    网格交易策略

    基于价格网格进行自动化买入卖出操作的策略
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化网格策略

        参数:
            config: 网格策略配置字典，包含:
                - etf_code: ETF代码
                - etf_name: ETF名称
                - base_price: 基准价
                - grid_spacing_up: 网格上涨间距(%)
                - grid_spacing_down: 网格下跌间距(%)
                - buy_amount: 每格买入金额/数量
                - sell_amount: 每格卖出金额/数量
                - buy_amount_type: 'shares' 或 'currency'
                - sell_amount_type: 'shares' 或 'currency'
                - created_date: 创建日期
                - expiry_date: 有效期
        """
        self.config = config
        self.etf_code = config['etf_code']
        self.etf_name = config['etf_name']
        self.base_price = config['base_price']
        self.grid_spacing_up = config['grid_spacing_up']  # 正数，如 5.0
        self.grid_spacing_down = config['grid_spacing_down']  # 负数，如 -5.0
        self.buy_amount = config['buy_amount']
        self.sell_amount = config['sell_amount']
        self.buy_amount_type = config['buy_amount_type']
        self.sell_amount_type = config['sell_amount_type']

        # 策略状态
        self.state = {
            'position': 0,  # 当前持仓（股数）
            'avg_cost': 0.0,  # 平均成本
            'total_buy_cost': 0.0,  # 总买入成本
            'total_sell_revenue': 0.0,  # 总卖出收入
            'grid_triggers': [],  # 网格触发历史
            'last_buy_price': 0.0,  # 最后买入价格
            'last_sell_price': 0.0,  # 最后卖出价格
        }

    def calculate_targets(self, total_value: float) -> Dict[str, float]:
        """
        计算目标配置

        网格策略不需要定期再平衡，目标配置基于网格触发

        参数:
            total_value: 总资产价值

        返回:
            Dict[str, float]: {ETF代码: 目标价值}
        """
        # 网格策略不需要预先计算目标
        # 目标由网格触发动态决定
        return {self.etf_code: 0.0}

    def check_rebalance_condition(self, current_date: str) -> bool:
        """
        检查是否需要再平衡

        网格策略不需要日历再平衡，只在价格触发网格时交易

        参数:
            current_date: 当前日期 (格式: YYYYMMDD)

        返回:
            bool: 网格策略总是返回 False，因为不使用日历再平衡
        """
        # 网格策略不使用日历再平衡
        return False

    def get_configuration(self) -> Dict[str, Any]:
        """
        获取策略配置

        返回:
            Dict[str, Any]: 策略配置信息
        """
        return {
            'strategy_name': 'GridTrading',
            'etf_code': self.etf_code,
            'etf_name': self.etf_name,
            'base_price': self.base_price,
            'grid_spacing_up': self.grid_spacing_up,
            'grid_spacing_down': self.grid_spacing_down,
            'buy_amount': self.buy_amount,
            'sell_amount': self.sell_amount,
            'buy_amount_type': self.buy_amount_type,
            'sell_amount_type': self.sell_amount_type,
        }

    def get_etf_universe(self) -> List[str]:
        """
        获取策略涉及的所有ETF代码

        返回:
            List[str]: ETF代码列表（网格策略只有1个ETF）
        """
        return [self.etf_code]

    def get_state(self) -> Dict[str, Any]:
        """
        获取当前策略状态

        返回:
            Dict[str, Any]: 策略状态信息
        """
        return self.state.copy()

    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        恢复策略状态

        参数:
            state: 策略状态信息
        """
        self.state = state.copy()

    def calculate_grid_levels(self, max_grids: int = 10) -> Dict[str, List[float]]:
        """
        计算网格价格层级

        参数:
            max_grids: 最大网格层数

        返回:
            Dict[str, List[float]]:
                {
                    'buy_grids': [买入价格1, 买入价格2, ...],
                    'sell_grids': [卖出价格1, 卖出价格2, ...]
                }
        """
        buy_grids = []
        sell_grids = []

        # 计算买入网格（向下）
        for i in range(1, max_grids + 1):
            grid_price = self.base_price * (1 + self.grid_spacing_down * i / 100)
            if grid_price > 0:  # 价格必须大于0
                buy_grids.append(grid_price)

        # 计算卖出网格（向上）
        for i in range(1, max_grids + 1):
            grid_price = self.base_price * (1 + self.grid_spacing_up * i / 100)
            sell_grids.append(grid_price)

        return {
            'buy_grids': sorted(buy_grids, reverse=True),  # 从高到低
            'sell_grids': sorted(sell_grids)  # 从低到高
        }

    def check_grid_trigger(self, current_price: float, grid_levels: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        检查是否触发网格交易

        参数:
            current_price: 当前价格
            grid_levels: 网格价格层级

        返回:
            Dict[str, Any]:
                {
                    'action': 'buy' | 'sell' | None,
                    'grid_price': float,
                    'grid_level': int,
                }
        """
        action = None
        grid_price = None
        grid_level = None

        # 检查买入网格
        for i, price in enumerate(grid_levels['buy_grids']):
            if current_price <= price:
                action = 'buy'
                grid_price = price
                grid_level = i + 1
                break

        # 如果没有触发买入，检查卖出网格
        if action is None:
            for i, price in enumerate(grid_levels['sell_grids']):
                if current_price >= price:
                    action = 'sell'
                    grid_price = price
                    grid_level = i + 1
                    break

        return {
            'action': action,
            'grid_price': grid_price,
            'grid_level': grid_level,
        }

    def get_buy_shares(self, current_price: float) -> float:
        """
        计算买入股数

        参数:
            current_price: 当前价格

        返回:
            float: 买入股数
        """
        if self.buy_amount_type == 'shares':
            # 按份买入
            return float(self.buy_amount)
        else:
            # 按金额买入
            if current_price > 0:
                return self.buy_amount / current_price
            else:
                return 0.0

    def get_sell_shares(self, current_position: float) -> float:
        """
        计算卖出股数

        参数:
            current_position: 当前持仓

        返回:
            float: 卖出股数
        """
        if self.sell_amount_type == 'shares':
            # 按份卖出
            sell_shares = min(float(self.sell_amount), current_position)
            return sell_shares
        else:
            # 按金额卖出（需要根据当前价格计算）
            # 这个方法需要当前价格参数，在Backtrader策略中会处理
            return current_position  # 返回全部持仓，由调用者决定

    def update_state(self, action: str, price: float, shares: float, grid_level: int) -> None:
        """
        更新策略状态

        参数:
            action: 'buy' 或 'sell'
            price: 成交价格
            shares: 成交股数
            grid_level: 网格层级
        """
        if action == 'buy':
            # 更新买入状态
            total_cost = self.state['total_buy_cost'] + price * shares
            total_shares = self.state['position'] + shares

            if total_shares > 0:
                self.state['avg_cost'] = total_cost / total_shares
            else:
                self.state['avg_cost'] = 0.0

            self.state['total_buy_cost'] = total_cost
            self.state['position'] = total_shares
            self.state['last_buy_price'] = price

        elif action == 'sell':
            # 更新卖出状态
            self.state['total_sell_revenue'] += price * shares
            self.state['position'] -= shares
            self.state['last_sell_price'] = price

        # 记录网格触发历史
        self.state['grid_triggers'].append({
            'action': action,
            'price': price,
            'shares': shares,
            'grid_level': grid_level,
            'position_after': self.state['position'],
        })

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        获取策略绩效摘要

        返回:
            Dict[str, Any]: 绩效摘要
        """
        total_trades = len(self.state['grid_triggers'])
        buy_trades = sum(1 for t in self.state['grid_triggers'] if t['action'] == 'buy')
        sell_trades = sum(1 for t in self.state['grid_triggers'] if t['action'] == 'sell')

        total_cost = self.state['total_buy_cost']
        total_revenue = self.state['total_sell_revenue']
        realized_profit = total_revenue - (self.state['position'] * self.state['avg_cost'] if self.state['position'] > 0 else 0)

        return {
            'etf_code': self.etf_code,
            'etf_name': self.etf_name,
            'current_position': self.state['position'],
            'avg_cost': self.state['avg_cost'],
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'total_buy_cost': total_cost,
            'total_sell_revenue': total_revenue,
            'unrealized_cost': self.state['position'] * self.state['avg_cost'],
            'realized_profit': realized_profit,
            'last_buy_price': self.state['last_buy_price'],
            'last_sell_price': self.state['last_sell_price'],
        }


# 测试代码
if __name__ == "__main__":
    # 测试网格策略
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from strategies.grid_config_parser import GridConfigParser

    # 解析配置
    parser = GridConfigParser()
    configs = parser.parse_table_xls("Table.xls")

    if configs:
        # 使用第一个配置测试
        config = configs[0]

        print("Grid Strategy Test")
        print("=" * 80)
        print(parser.format_config_summary(config))

        # 创建策略
        strategy = GridStrategy(config)

        # 测试网格计算
        print("\nGrid Levels (max 5):")
        grid_levels = strategy.calculate_grid_levels(max_grids=5)
        print(f"Buy Grids: {[f'{p:.3f}' for p in grid_levels['buy_grids']]}")
        print(f"Sell Grids: {[f'{p:.3f}' for p in grid_levels['sell_grids']]}")

        # 测试网格触发
        test_prices = [1.40, 1.50, 1.57, 1.65, 1.75]
        print(f"\nGrid Trigger Tests (Base Price: {strategy.base_price}):")
        for price in test_prices:
            trigger = strategy.check_grid_trigger(price, grid_levels)
            print(f"Price {price:.3f}: {trigger}")

        # 测试配置
        print(f"\nStrategy Configuration:")
        cfg = strategy.get_configuration()
        for key, value in cfg.items():
            print(f"  {key}: {value}")

        # 测试ETF列表
        print(f"\nETF Universe: {strategy.get_etf_universe()}")

        print("\n[OK] Grid Strategy Test Completed")
