# encoding:utf-8
"""
网格交易策略 - Backtrader实现
在Backtrader框架中实现网格交易策略
"""
import backtrader as bt
from typing import List, Dict, Any
from datetime import datetime


class GridTradingStrategy(bt.Strategy):
    """
    网格交易策略 - Backtrader实现

    基于价格网格进行自动买入卖出的策略
    """

    params = (
        ('base_price', 1.0),           # 基准价格
        ('grid_spacing_up', 5.0),      # 网格上涨间距(%)
        ('grid_spacing_down', -5.0),   # 网格下跌间距(%)
        ('buy_amount', 1000.0),        # 每格买入数量
        ('sell_amount', 1000.0),       # 每格卖出数量
        ('buy_amount_type', 'shares'), # 'shares' 或 'currency'
        ('sell_amount_type', 'shares'), # 'shares' 或 'currency'
        ('max_grids', 10),             # 最大网格层数
        ('printlog', True),            # 是否打印日志
    )

    def __init__(self):
        """初始化策略"""
        # 计算网格层级
        self.buy_grids = []
        self.sell_grids = []

        for i in range(1, self.params.max_grids + 1):
            # 买入网格（向下）
            buy_grid_price = self.params.base_price * (1 + self.params.grid_spacing_down * i / 100)
            if buy_grid_price > 0:
                self.buy_grids.append(buy_grid_price)

            # 卖出网格（向上）
            sell_grid_price = self.params.base_price * (1 + self.params.grid_spacing_up * i / 100)
            self.sell_grids.append(sell_grid_price)

        # 排序
        self.buy_grids.sort(reverse=True)  # 从高到低
        self.sell_grids.sort()  # 从低到高

        # 记录已触发的网格（避免重复触发）
        self.triggered_buy_grids = set()
        self.triggered_sell_grids = set()

        # 记录持仓统计
        self.total_buy_cost = 0.0
        self.total_shares_bought = 0.0
        self.total_sell_revenue = 0.0
        self.total_shares_sold = 0.0

        # 网格触发历史
        self.grid_triggers = []  # {'date', 'action', 'price', 'grid_level', 'shares', 'amount'}

        if self.params.printlog:
            self.log(f'Grid Trading Strategy Initialized')
            self.log(f'Base Price: {self.params.base_price:.3f}')
            self.log(f'Buy Grids: {[f"{g:.3f}" for g in self.buy_grids[:5]]}...')
            self.log(f'Sell Grids: {[f"{g:.3f}" for g in self.sell_grids[:5]]}...')

    def log(self, txt, dt=None):
        """日志输出"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')

    def next(self):
        """
        每个bar调用一次
        检查是否触发网格交易
        """
        current_date = self.datas[0].datetime.date(0)
        current_close = self.datas[0].close[0]
        current_high = self.datas[0].high[0]
        current_low = self.datas[0].low[0]

        # 检查买入网格触发（使用Low价格）
        for i, grid_price in enumerate(self.buy_grids):
            grid_level = i + 1

            # 如果价格触及或跌破买入网格，且该网格尚未触发
            if current_low <= grid_price and grid_level not in self.triggered_buy_grids:
                # 检查是否有足够资金
                buy_shares = self._calculate_buy_shares(grid_price)
                required_cash = buy_shares * grid_price

                if self.broker.getvalue() >= required_cash:
                    self._execute_buy(grid_price, grid_level, buy_shares)
                    self.triggered_buy_grids.add(grid_level)
                else:
                    self.log(f'Insufficient cash for buy grid {grid_level}: need {required_cash:.2f}, have {self.broker.getvalue():.2f}')

        # 检查卖出网格触发（使用High价格）
        for i, grid_price in enumerate(self.sell_grids):
            grid_level = i + 1

            # 如果价格触及或突破卖出网格，且该网格尚未触发，且有持仓
            if current_high >= grid_price and grid_level not in self.triggered_sell_grids:
                current_position = self.getposition(self.datas[0]).size

                if current_position > 0:
                    sell_shares = self._calculate_sell_shares(current_position, grid_price)

                    if sell_shares > 0:
                        self._execute_sell(grid_price, grid_level, sell_shares)
                        self.triggered_sell_grids.add(grid_level)
                else:
                    self.log(f'No position to sell for grid {grid_level}')

    def _calculate_buy_shares(self, price: float) -> float:
        """
        计算买入股数

        参数:
            price: 买入价格

        返回:
            float: 买入股数
        """
        if self.params.buy_amount_type == 'shares':
            return float(self.params.buy_amount)
        else:  # currency
            if price > 0:
                return self.params.buy_amount / price
            else:
                return 0.0

    def _calculate_sell_shares(self, current_position: float, price: float) -> float:
        """
        计算卖出股数

        参数:
            current_position: 当前持仓
            price: 卖出价格

        返回:
            float: 卖出股数
        """
        if self.params.sell_amount_type == 'shares':
            # 按份卖出，但不能超过持仓
            return min(float(self.params.sell_amount), current_position)
        else:  # currency
            # 按金额卖出
            if price > 0:
                sell_shares = self.params.sell_amount / price
                return min(sell_shares, current_position)
            else:
                return 0.0

    def _execute_buy(self, price: float, grid_level: int, shares: float):
        """
        执行买入订单

        参数:
            price: 目标价格
            grid_level: 网格层级
            shares: 买入股数
        """
        # 下单（使用限价单，价格设为当前价格）
        order = self.buy(size=shares)

        # 记录订单信息
        order.addinfo(action='buy', grid_level=grid_level, target_price=price)

        if self.params.printlog:
            self.log(f'BUY ORDER CREATED: Grid {grid_level}, Price: {price:.3f}, Shares: {shares:.0f}')

    def _execute_sell(self, price: float, grid_level: int, shares: float):
        """
        执行卖出订单

        参数:
            price: 目标价格
            grid_level: 网格层级
            shares: 卖出股数
        """
        # 下单（使用限价单，价格设为当前价格）
        order = self.sell(size=shares)

        # 记录订单信息
        order.addinfo(action='sell', grid_level=grid_level, target_price=price)

        if self.params.printlog:
            self.log(f'SELL ORDER CREATED: Grid {grid_level}, Price: {price:.3f}, Shares: {shares:.0f}')

    def notify_order(self, order):
        """
        订单状态通知

        参数:
            order: 订单对象
        """
        if order.status in [order.Submitted, order.Accepted, order.Partial]:
            return  # 订单还在进行中

        if order.status in [order.Completed]:
            # 订单完成
            if order.isbuy():
                self._on_buy_completed(order)
            else:
                self._on_sell_completed(order)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单失败
            self.log(f'Order Failed: Status={order.getstatusname()}')

    def _on_buy_completed(self, order):
        """买入订单完成处理"""
        executed_price = order.executed.price
        executed_size = order.executed.size
        executed_value = order.executed.value

        self.total_buy_cost += executed_value
        self.total_shares_bought += executed_size

        # 记录网格触发
        grid_level = getattr(order, 'grid_level', 0)
        target_price = getattr(order, 'target_price', 0)

        self.grid_triggers.append({
            'date': self.datas[0].datetime.date(0),
            'action': 'buy',
            'price': executed_price,
            'grid_level': grid_level,
            'target_price': target_price,
            'shares': executed_size,
            'amount': executed_value,
        })

        self.log(f'BUY EXECUTED: Grid {grid_level}, Price: {executed_price:.3f}, Shares: {executed_size:.0f}, Value: {executed_value:.2f}')

    def _on_sell_completed(self, order):
        """卖出订单完成处理"""
        executed_price = order.executed.price
        executed_size = order.executed.size
        executed_value = order.executed.value

        self.total_sell_revenue += executed_value
        self.total_shares_sold += executed_size

        # 记录网格触发
        grid_level = getattr(order, 'grid_level', 0)
        target_price = getattr(order, 'target_price', 0)

        self.grid_triggers.append({
            'date': self.datas[0].datetime.date(0),
            'action': 'sell',
            'price': executed_price,
            'grid_level': grid_level,
            'target_price': target_price,
            'shares': executed_size,
            'amount': executed_value,
        })

        self.log(f'SELL EXECUTED: Grid {grid_level}, Price: {executed_price:.3f}, Shares: {executed_size:.0f}, Value: {executed_value:.2f}')

    def notify_trade(self, trade):
        """
        交易完成通知（每次开仓+平仓为一对）

        参数:
            trade: 交易对象
        """
        if trade.isclosed:
            gross_pnl = trade.pnl  # 毛利润（不含手续费）
            net_pnl = trade.pnlcomm  # 净利润（含手续费）

            self.log(f'TRADE CLOSED: Gross PnL: {gross_pnl:.2f}, Net PnL: {net_pnl:.2f}')

    def stop(self):
        """策略结束"""
        final_value = self.broker.getvalue()
        final_position = self.getposition(self.datas[0]).size

        self.log('=' * 80)
        self.log(f'STRATEGY END')
        self.log(f'Final Portfolio Value: {final_value:.2f}')
        self.log(f'Final Position: {final_position:.0f} shares')
        self.log(f'Total Buy Cost: {self.total_buy_cost:.2f}')
        self.log(f'Total Sell Revenue: {self.total_sell_revenue:.2f}')
        self.log(f'Total Shares Bought: {self.total_shares_bought:.0f}')
        self.log(f'Total Shares Sold: {self.total_shares_sold:.0f}')
        self.log(f'Total Grid Triggers: {len(self.grid_triggers)}')
        self.log(f'Buy Triggers: {sum(1 for t in self.grid_triggers if t["action"] == "buy")}')
        self.log(f'Sell Triggers: {sum(1 for t in self.grid_triggers if t["action"] == "sell")}')
        self.log('=' * 80)

    def get_grid_triggers(self) -> List[Dict[str, Any]]:
        """获取网格触发历史"""
        return self.grid_triggers.copy()

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取绩效摘要"""
        final_value = self.broker.getvalue()
        final_position = self.getposition(self.datas[0]).size

        # 计算平均成本
        avg_cost = self.total_buy_cost / self.total_shares_bought if self.total_shares_bought > 0 else 0

        # 计算未实现盈亏
        if final_position > 0:
            current_price = self.datas[0].close[0]
            unrealized_pnl = (current_price - avg_cost) * final_position
        else:
            unrealized_pnl = 0

        # 已实现盈亏
        realized_pnl = self.total_sell_revenue - (self.total_shares_sold * avg_cost)

        return {
            'final_value': final_value,
            'final_position': final_position,
            'avg_cost': avg_cost,
            'total_buy_cost': self.total_buy_cost,
            'total_sell_revenue': self.total_sell_revenue,
            'total_shares_bought': self.total_shares_bought,
            'total_shares_sold': self.total_shares_sold,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_triggers': len(self.grid_triggers),
            'buy_triggers': sum(1 for t in self.grid_triggers if t['action'] == 'buy'),
            'sell_triggers': sum(1 for t in self.grid_triggers if t['action'] == 'sell'),
        }


# 测试代码
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    print("GridTradingStrategy - Backtrader Implementation")
    print("This module should be used with Backtrader Cerebro engine")
    print("\nExample usage:")
    print("""
    import backtrader as bt
    from backtesting.grid_bt_strategy import GridTradingStrategy

    cerebro = bt.Cerebro()
    cerebro.addstrategy(GridTradingStrategy,
                      base_price=1.573,
                      grid_spacing_up=5.0,
                      grid_spacing_down=-5.0,
                      buy_amount=80000,
                      sell_amount=80000,
                      buy_amount_type='shares',
                      sell_amount_type='shares')
    """)
