# encoding:utf-8
"""
交易记录器 - Backtrader Analyzer
记录回测过程中的所有订单和交易对数据
"""
import backtrader as bt
from datetime import datetime


class TradeRecorder(bt.Analyzer):
    """
    自定义Analyzer：记录订单和交易对

    功能：
    - 记录每个订单的完整信息（日期、标的、方向、价格、数量、手续费等）
    - 记录每个交易对的完整信息（开仓/平仓信息、盈亏、持仓天数等）
    """

    def __init__(self):
        """初始化记录器"""
        # 订单记录列表
        self.orders = []

        # 交易对记录列表
        self.trades = []

        # ID计数器
        self.order_id = 0
        self.trade_id = 0

        # 跟踪是否是第一次再平衡（用于添加备注）
        self.is_first_rebalance = True

    def notify_order(self, order):
        """
        订单状态通知

        记录订单执行信息
        """
        # 只记录已完成的订单
        if order.status == order.Completed:
            self.order_id += 1

            # 转换日期（Backtrader使用数字存储日期）
            order_datetime = bt.num2date(order.executed.dt)

            # 提取订单信息
            order_record = {
                '订单ID': self.order_id,
                '日期': order_datetime.strftime('%Y-%m-%d'),
                '时间': order_datetime.strftime('%H:%M:%S'),
                '标的': order.data._name,
                '方向': '买入' if order.isbuy() else '卖出',
                '订单类型': '市价单',  # Backtrader默认是市价单
                '成交价格': round(order.executed.price, 3),
                '成交数量': int(order.executed.size),
                '成交金额': round(order.executed.value, 2),
                '手续费': round(order.executed.comm, 2),
                '状态': '已完成',
                '备注': self._get_order_remark()
            }

            # 添加到订单列表
            self.orders.append(order_record)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 记录失败的订单
            self.order_id += 1

            order_record = {
                '订单ID': self.order_id,
                '日期': datetime.now().strftime('%Y-%m-%d'),
                '时间': datetime.now().strftime('%H:%M:%S'),
                '标的': order.data._name if hasattr(order, 'data') and order.data else 'N/A',
                '方向': '买入' if order.isbuy() else '卖出',
                '订单类型': '市价单',
                '成交价格': 0,
                '成交数量': 0,
                '成交金额': 0,
                '手续费': 0,
                '状态': order.getstatusname(),
                '备注': '订单执行失败'
            }

            self.orders.append(order_record)

    def notify_trade(self, trade):
        """
        交易完成通知

        记录交易对信息（仅在交易关闭时）
        """
        # 只记录已关闭的交易
        if trade.isclosed:
            self.trade_id += 1

            # 从trade.history获取开仓和平仓信息
            history = trade.history

            if len(history) > 0:
                # 开仓信息
                open_event = history[0]
                open_date = bt.num2date(open_event.dt)
                open_price = open_event.price
                open_size = open_event.size

                # 平仓信息
                close_event = history[-1]
                close_date = bt.num2date(close_event.dt)
                close_price = close_event.price
                close_size = close_event.size

                # 计算持仓天数
                holding_days = (close_date - open_date).days

                # 计算收益率
                if open_price > 0 and open_size > 0:
                    open_value = open_price * abs(open_size)
                    return_pct = (trade.pnlcomm / open_value) * 100 if open_value > 0 else 0
                else:
                    return_pct = 0

                # 提取交易对信息
                trade_record = {
                    '交易ID': self.trade_id,
                    '标的': trade.data._name,
                    '开仓日期': open_date.strftime('%Y-%m-%d'),
                    '开仓价格': round(open_price, 3),
                    '开仓数量': int(open_size),
                    '平仓日期': close_date.strftime('%Y-%m-%d'),
                    '平仓价格': round(close_price, 3),
                    '平仓数量': int(close_size),
                    '盈亏金额': round(trade.pnl, 2),
                    '手续费': round(trade.commission, 2),
                    '净盈亏': round(trade.pnlcomm, 2),
                    '收益率': f'{return_pct:.2f}%',
                    '持仓天数': holding_days
                }

                # 添加到交易对列表
                self.trades.append(trade_record)

    def _get_order_remark(self):
        """
        获取订单备注

        根据当前状态判断订单类型（初始建仓或再平衡）
        """
        if self.is_first_rebalance:
            self.is_first_rebalance = False
            return '初始建仓'
        else:
            return '再平衡'

    def get_analysis(self):
        """
        返回分析结果

        返回:
            dict: 包含订单列表和交易对列表
        """
        return {
            'orders': self.orders,
            'trades': self.trades
        }
