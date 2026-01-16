# encoding:utf-8
"""
全天候Backtrader策略实现
将全天候策略逻辑封装为Backtrader策略
"""
import backtrader as bt
from datetime import datetime
from typing import Dict, List


class AllWeatherStrategy(bt.Strategy):
    """
    全天候资产配置策略 - Backtrader版本

    实现25%商品、25%股票、25%长债、25%短债的资产配置
    """

    params = (
        ('position_ratio', 0.5),          # 仓位比例
        ('rebalance_period', 60),          # 再平衡周期(天)
        ('etf_allocation', {}),            # ETF配置 {category: [etfs]}
        ('category_weights', {             # 类别权重
            'commodities': 0.25,
            'stocks': 0.25,
            'long_bonds': 0.25,
            'short_bonds': 0.25
        }),
    )

    def __init__(self):
        """初始化策略"""
        # 状态变量
        self.last_rebalance = None
        self.rebalance_counter = 0
        self.rebalance_dates = []

        # 计算每个ETF的目标权重
        self.target_weights = self._calculate_etf_weights()

        # 记录数据源
        self.data_names = [d._name for d in self.datas]
        self.data_by_name = {d._name: d for d in self.datas}

        print(f"\n策略初始化完成")
        print(f"数据源数量: {len(self.datas)}")
        print(f"再平衡周期: {self.params.rebalance_period}天")
        print(f"仓位比例: {self.params.position_ratio*100:.1f}%")
        print(f"目标权重: {self.target_weights}\n")

    def _calculate_etf_weights(self) -> Dict[str, float]:
        """
        计算每个ETF的目标权重

        返回:
            dict: {etf_code: weight}
        """
        weights = {}

        for category, etfs in self.params.etf_allocation.items():
            category_weight = self.params.category_weights.get(category, 0.25)
            etf_weight = (category_weight * self.params.position_ratio) / len(etfs)

            for etf in etfs:
                weights[etf] = etf_weight

        return weights

    def next(self):
        """
        每个K线调用一次
        这是Backtrader的主策略方法
        """
        # 获取当前日期
        current_date = self.datas[0].datetime.date(0)
        self.rebalance_counter += 1

        # 检查是否需要再平衡
        if self._should_rebalance(current_date):
            print(f"\n{'='*60}")
            print(f"执行再平衡: {current_date}")
            print(f"当前总资产: {self.broker.getvalue():,.2f}")
            print(f"{'='*60}")

            self._rebalance_portfolio()
            self.last_rebalance = current_date
            self.rebalance_counter = 0
            self.rebalance_dates.append(current_date)

    def _should_rebalance(self, current_date) -> bool:
        """
        检查是否需要再平衡

        参数:
            current_date: 当前日期

        返回:
            bool: 是否需要再平衡
        """
        # 第一次执行时需要再平衡
        if self.last_rebalance is None:
            return True

        # 检查是否达到再平衡周期
        if self.rebalance_counter >= self.params.rebalance_period:
            return True

        return False

    def _rebalance_portfolio(self):
        """
        执行投资组合再平衡
        """
        total_value = self.broker.getvalue()
        target_value = total_value * self.params.position_ratio

        print(f"\n目标投资金额: {target_value:,.2f}")
        print(f"当前持仓:")
        print(f"{'ETF代码':<15} {'当前数量':>10} {'当前价格':>10} {'当前市值':>15} {'目标数量':>10} {'调整':>10}")
        print("-" * 80)

        # 对每个ETF进行再平衡
        for data in self.datas:
            etf_code = data._name

            # 跳过不在配置中的ETF
            if etf_code not in self.target_weights:
                continue

            target_weight = self.target_weights[etf_code]
            target_value_etf = target_value * target_weight

            # 获取当前持仓
            current_position = self.getposition(data).size
            current_price = data.close[0]
            current_value = current_position * current_price

            # 计算目标持仓量（按手，100股一手）
            target_position = int(target_value_etf / current_price / 100) * 100

            # 打印当前状态
            action = ""
            if target_position > current_position:
                action = f"+{target_position - current_position}"
            elif target_position < current_position:
                action = f"{target_position - current_position}"

            print(f"{etf_code:<15} {current_position:>10} {current_price:>10.2f} {current_value:>15,.2f} {target_position:>10} {action:>10}")

            # 执行再平衡
            if target_position > current_position:
                # 买入
                buy_size = target_position - current_position
                if buy_size > 0:
                    self.buy(data=data, size=buy_size)
                    print(f"  -> 买入 {buy_size} 股")

            elif target_position < current_position:
                # 卖出
                sell_size = current_position - target_position
                if sell_size > 0:
                    self.sell(data=data, size=sell_size)
                    print(f"  -> 卖出 {sell_size} 股")

        print("-" * 80)

    def stop(self):
        """
        策略结束时调用
        """
        print("\n" + "=" * 80)
        print("策略执行完成")
        print("=" * 80)
        print(f"再平衡次数: {len(self.rebalance_dates)}")
        print(f"再平衡日期: {[str(d) for d in self.rebalance_dates]}")
        print(f"最终资产: {self.broker.getvalue():,.2f}")

    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"买入完成: {order.data._name} - "
                      f"价格: {order.executed.price:.2f}, "
                      f"数量: {order.executed.size}, "
                      f"金额: {order.executed.value:.2f}")
            else:
                print(f"卖出完成: {order.data._name} - "
                      f"价格: {order.executed.price:.2f}, "
                      f"数量: {order.executed.size}, "
                      f"金额: {order.executed.value:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"订单失败: {order.data._name} - 状态: {order.getstatusname()}")

    def notify_trade(self, trade):
        """
        交易完成通知
        """
        if trade.isclosed:
            print(f"交易关闭: {trade.data._name} - "
                  f"利润: {trade.pnl:.2f}, "
                  f"净值: {trade.pnlcomm:.2f}")
