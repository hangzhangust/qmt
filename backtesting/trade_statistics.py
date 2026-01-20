# encoding:utf-8
"""
交易统计工具类
从交易记录中计算汇总统计数据
"""
import numpy as np
from typing import List, Dict, Any


class TradeStatistics:
    """
    交易统计工具类

    功能：
    - 从交易记录中计算汇总统计数据
    - 计算胜率、平均盈亏、盈亏比、持仓时间等指标
    """

    @staticmethod
    def calculate_summary(trades_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算交易汇总统计

        参数:
            trades_records: 交易记录列表

        返回:
            dict: 交易汇总统计指标
        """
        if not trades_records or len(trades_records) == 0:
            return {
                '总交易次数': 0,
                '盈利交易次数': 0,
                '亏损交易次数': 0,
                '胜率': '0.00%',
                '平均盈利金额': 0,
                '平均亏损金额': 0,
                '盈亏比': '0.00:1',
                '最大单笔盈利': 0,
                '最大单笔亏损': 0,
                '平均持仓天数': 0,
                '最短持仓天数': 0,
                '最长持仓天数': 0,
                '总手续费': 0,
                '总交易金额': 0
            }

        # 基础统计
        total_trades = len(trades_records)
        won_trades = [t for t in trades_records if t.get('净盈亏', 0) > 0]
        lost_trades = [t for t in trades_records if t.get('净盈亏', 0) < 0]

        won_count = len(won_trades)
        lost_count = len(lost_trades)

        # 胜率
        win_rate = (won_count / total_trades * 100) if total_trades > 0 else 0

        # 平均盈利/亏损金额
        if won_count > 0:
            avg_profit = np.mean([t.get('净盈亏', 0) for t in won_trades])
            max_profit = np.max([t.get('净盈亏', 0) for t in won_trades])
        else:
            avg_profit = 0
            max_profit = 0

        if lost_count > 0:
            avg_loss = np.mean([t.get('净盈亏', 0) for t in lost_trades])
            max_loss = np.min([t.get('净盈亏', 0) for t in lost_trades])
        else:
            avg_loss = 0
            max_loss = 0

        # 盈亏比
        if avg_loss != 0:
            profit_loss_ratio = abs(avg_profit / avg_loss)
        else:
            profit_loss_ratio = 0

        # 持仓天数统计
        holding_days = [t.get('持仓天数', 0) for t in trades_records if t.get('持仓天数', 0) > 0]
        if holding_days:
            avg_holding_days = np.mean(holding_days)
            min_holding_days = np.min(holding_days)
            max_holding_days = np.max(holding_days)
        else:
            avg_holding_days = 0
            min_holding_days = 0
            max_holding_days = 0

        # 总手续费
        total_commission = np.sum([t.get('手续费', 0) for t in trades_records])

        # 总交易金额（粗略估计：开仓金额+平仓金额）
        total_trade_amount = np.sum([
            abs(t.get('开仓价格', 0) * t.get('开仓数量', 0)) +
            abs(t.get('平仓价格', 0) * t.get('平仓数量', 0))
            for t in trades_records
        ])

        # 构建统计结果
        summary = {
            '总交易次数': total_trades,
            '盈利交易次数': won_count,
            '亏损交易次数': lost_count,
            '胜率': f'{win_rate:.2f}%',
            '平均盈利金额': round(avg_profit, 2),
            '平均亏损金额': round(avg_loss, 2),
            '盈亏比': f'{profit_loss_ratio:.2f}:1',
            '最大单笔盈利': round(max_profit, 2),
            '最大单笔亏损': round(max_loss, 2),
            '平均持仓天数': round(avg_holding_days, 0),
            '最短持仓天数': int(min_holding_days),
            '最长持仓天数': int(max_holding_days),
            '总手续费': round(total_commission, 2),
            '总交易金额': round(total_trade_amount, 2)
        }

        return summary

    @staticmethod
    def calculate_win_rate(trades_records: List[Dict[str, Any]]) -> float:
        """
        计算胜率

        参数:
            trades_records: 交易记录列表

        返回:
            float: 胜率（0-100）
        """
        if not trades_records:
            return 0.0

        won_count = sum(1 for t in trades_records if t.get('净盈亏', 0) > 0)
        return (won_count / len(trades_records) * 100) if len(trades_records) > 0 else 0

    @staticmethod
    def calculate_avg_holding_period(trades_records: List[Dict[str, Any]]) -> float:
        """
        计算平均持仓时间

        参数:
            trades_records: 交易记录列表

        返回:
            float: 平均持仓天数
        """
        if not trades_records:
            return 0.0

        holding_days = [t.get('持仓天数', 0) for t in trades_records if t.get('持仓天数', 0) > 0]

        if not holding_days:
            return 0.0

        return np.mean(holding_days)

    @staticmethod
    def calculate_profit_factor(trades_records: List[Dict[str, Any]]) -> float:
        """
        计算盈亏比（盈利因子）

        参数:
            trades_records: 交易记录列表

        返回:
            float: 盈亏比
        """
        if not trades_records:
            return 0.0

        gross_profit = np.sum([t.get('净盈亏', 0) for t in trades_records if t.get('净盈亏', 0) > 0])
        gross_loss = abs(np.sum([t.get('净盈亏', 0) for t in trades_records if t.get('净盈亏', 0) < 0]))

        return (gross_profit / gross_loss) if gross_loss != 0 else 0
