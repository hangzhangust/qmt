# encoding:utf-8
"""
持仓跟踪器 - Backtrader Observer
记录每日持仓状态和汇总信息
"""
import backtrader as bt
import numpy as np


class PositionTracker(bt.Observer):
    """
    自定义Observer：跟踪每日持仓

    功能：
    - 在每个交易日结束时记录所有ETF的持仓状态
    - 记录总资产、现金、持仓占比等汇总信息
    - 生成每日详细持仓和每日汇总两份数据
    """

    lines = ('total_value', 'cash', 'position_value')

    plotinfo = dict(
        plot=False,  # 不绘制图表
    )

    def __init__(self, **kwargs):
        """初始化跟踪器"""
        # 调用父类初始化
        super(PositionTracker, self).__init__(**kwargs)

        # 每日详细持仓记录列表
        self.daily_positions = []

        # 每日汇总记录列表
        self.daily_summary = []

        # 上一日的日期（用于判断是否是新的一天）
        self.last_date = None

    def next(self):
        """
        每个K线结束时调用

        记录当前持仓状态
        """
        # 获取当前日期
        current_date = self.data.datetime.date(0)

        # 如果是同一天，跳过（避免重复记录）
        if self.last_date == current_date:
            return

        self.last_date = current_date

        # 在Observer中，通过self._owner访问strategy
        strategy = self._owner
        if not hasattr(strategy, 'broker'):
            return

        # 获取账户信息
        total_value = strategy.broker.getvalue()
        cash = strategy.broker.getcash()
        position_value = total_value - cash

        # 记录每个ETF的持仓
        etf_records = []
        profit_etf_count = 0
        loss_etf_count = 0
        max_profit_etf = {'code': 'N/A', 'pnl_pct': 0}
        max_loss_etf = {'code': 'N/A', 'pnl_pct': 0}

        for data in strategy.datas:
            # 获取持仓
            position = strategy.getposition(data)

            # 只记录有持仓的ETF
            if position.size != 0:
                etf_code = data._name
                current_price = data.close[0]

                # 跳过价格无效的情况
                if np.isnan(current_price) or current_price == 0:
                    continue

                cost_price = position.price
                market_value = position.size * current_price
                cost_basis = position.size * cost_price
                unrealized_pnl = market_value - cost_basis

                # 计算盈亏比例
                if cost_basis > 0:
                    pnl_pct = (unrealized_pnl / cost_basis) * 100
                else:
                    pnl_pct = 0

                # 获取目标权重（从strategy的target_weights）
                target_weight = strategy.target_weights.get(etf_code, 0)
                actual_weight = market_value / total_value if total_value > 0 else 0
                deviation = actual_weight - target_weight

                # 持仓记录
                etf_record = {
                    '日期': current_date.strftime('%Y-%m-%d'),
                    '标的': etf_code,
                    '持仓数量': int(position.size),
                    '持仓价格': round(cost_price, 3),
                    '当前价格': round(current_price, 3),
                    '市值': round(market_value, 2),
                    '成本': round(cost_basis, 2),
                    '浮动盈亏': round(unrealized_pnl, 2),
                    '盈亏比例': f'{pnl_pct:.2f}%',
                    '目标权重': f'{target_weight * 100:.2f}%',
                    '实际权重': f'{actual_weight * 100:.2f}%',
                    '偏离度': f'{deviation * 100:+.2f}%',
                    '总资产': round(total_value, 2),
                    '现金': round(cash, 2)
                }

                etf_records.append(etf_record)

                # 统计盈利/亏损ETF数量
                if unrealized_pnl > 0:
                    profit_etf_count += 1
                    if pnl_pct > max_profit_etf['pnl_pct']:
                        max_profit_etf = {'code': etf_code, 'pnl_pct': pnl_pct}
                elif unrealized_pnl < 0:
                    loss_etf_count += 1
                    if pnl_pct < max_loss_etf['pnl_pct']:
                        max_loss_etf = {'code': etf_code, 'pnl_pct': pnl_pct}

        # 将所有ETF记录添加到每日持仓列表
        self.daily_positions.extend(etf_records)

        # 记录汇总信息
        position_ratio = (position_value / total_value * 100) if total_value > 0 else 0
        etf_count = len(etf_records)

        summary_record = {
            '日期': current_date.strftime('%Y-%m-%d'),
            '总资产': round(total_value, 2),
            '现金': round(cash, 2),
            '持仓市值': round(position_value, 2),
            '持仓占比': f'{position_ratio:.2f}%',
            'ETF数量': etf_count,
            '盈利ETF数': profit_etf_count,
            '亏损ETF数': loss_etf_count,
            '最大盈利ETF': max_profit_etf['code'] if max_profit_etf['pnl_pct'] > 0 else 'N/A',
            '最大盈利比例': f"{max_profit_etf['pnl_pct']:.2f}%" if max_profit_etf['pnl_pct'] > 0 else '0.00%',
            '最大亏损ETF': max_loss_etf['code'] if max_loss_etf['pnl_pct'] < 0 else 'N/A',
            '最大亏损比例': f"{max_loss_etf['pnl_pct']:.2f}%" if max_loss_etf['pnl_pct'] < 0 else '0.00%'
        }

        self.daily_summary.append(summary_record)

    def get_analysis(self):
        """
        返回分析结果

        返回:
            dict: 包含每日持仓列表和每日汇总列表
        """
        return {
            'daily_positions': self.daily_positions,
            'daily_summary': self.daily_summary
        }
