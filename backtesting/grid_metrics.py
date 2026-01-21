# encoding:utf-8
"""
网格交易策略指标分析模块
计算网格交易特有的性能指标
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime


class GridMetricsAnalyzer:
    """
    网格交易策略指标分析器

    计算网格交易特有的效率和性能指标
    """

    @staticmethod
    def calculate_basic_metrics(
        grid_triggers: List[Dict[str, Any]],
        final_value: float,
        initial_cash: float,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        计算基础网格指标

        参数:
            grid_triggers: 网格触发历史列表
            final_value: 最终资产价值
            initial_cash: 初始资金
            start_date: 回测开始日期 (YYYYMMDD)
            end_date: 回测结束日期 (YYYYMMDD)

        返回:
            Dict: 包含所有基础指标的字典
        """
        # 1. 网格效率指标
        efficiency_metrics = GridMetricsAnalyzer.calculate_grid_efficiency(
            grid_triggers, start_date, end_date
        )

        # 2. 收益指标
        return_metrics = GridMetricsAnalyzer.calculate_returns(
            final_value, initial_cash, grid_triggers
        )

        # 3. 合并所有指标
        metrics = {
            **efficiency_metrics,
            **return_metrics,
            'final_value': final_value,
            'initial_cash': initial_cash,
        }

        return metrics

    @staticmethod
    def calculate_grid_efficiency(
        grid_triggers: List[Dict[str, Any]],
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        计算网格效率指标

        参数:
            grid_triggers: 网格触发历史
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        返回:
            Dict: 网格效率指标
        """
        if not grid_triggers:
            return {
                'total_grid_triggers': 0,
                'buy_grid_triggers': 0,
                'sell_grid_triggers': 0,
                'grid_trigger_frequency': 0.0,
                'unique_grids_used': 0,
            }

        total_triggers = len(grid_triggers)
        buy_triggers = sum(1 for t in grid_triggers if t['action'] == 'buy')
        sell_triggers = sum(1 for t in grid_triggers if t['action'] == 'sell')

        # 计算使用的不同网格层级
        unique_grids = len(set(t['grid_level'] for t in grid_triggers))

        # 计算触发频率（次/月）
        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
        end_dt = pd.to_datetime(end_date, format='%Y%m%d')
        months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month) + 1

        frequency = total_triggers / months if months > 0 else 0

        return {
            'total_grid_triggers': total_triggers,
            'buy_grid_triggers': buy_triggers,
            'sell_grid_triggers': sell_triggers,
            'grid_trigger_frequency': round(frequency, 2),
            'unique_grids_used': unique_grids,
        }

    @staticmethod
    def calculate_returns(
        final_value: float,
        initial_cash: float,
        grid_triggers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算收益指标

        参数:
            final_value: 最终资产价值
            initial_cash: 初始资金
            grid_triggers: 网格触发历史

        返回:
            Dict: 收益指标
        """
        total_return = (final_value - initial_cash) / initial_cash * 100 if initial_cash > 0 else 0

        # 计算已实现和未实现盈亏
        realized_pnl = 0.0
        unrealized_pnl = 0.0

        # 简化的盈亏计算（实际应该从成交记录计算）
        buy_amount = sum(t['amount'] for t in grid_triggers if t['action'] == 'buy')
        sell_amount = sum(t['amount'] for t in grid_triggers if t['action'] == 'sell')

        # 这是一个简化的估算，实际应该使用更精确的方法
        if sell_amount > 0:
            # 假设卖出的盈亏为简化计算
            buy_shares = sum(t['shares'] for t in grid_triggers if t['action'] == 'buy')
            sell_shares = sum(t['shares'] for t in grid_triggers if t['action'] == 'sell')
            if buy_shares > 0:
                avg_cost = buy_amount / buy_shares
                avg_revenue = sell_amount / sell_shares if sell_shares > 0 else 0
                realized_pnl = (avg_revenue - avg_cost) * sell_shares

        return {
            'total_return': round(total_return, 2),
            'total_pnl': round(final_value - initial_cash, 2),
            'realized_pnl': round(realized_pnl, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'total_trades': len(grid_triggers),
        }

    @staticmethod
    def analyze_grid_distribution(grid_triggers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析网格层级分布

        参数:
            grid_triggers: 网格触发历史

        返回:
            Dict: 网格层级分布统计
        """
        if not grid_triggers:
            return {}

        # 统计每个网格层级的触发次数
        grid_distribution = {}
        for trigger in grid_triggers:
            level = trigger['grid_level']
            action = trigger['action']

            if level not in grid_distribution:
                grid_distribution[level] = {'buy': 0, 'sell': 0, 'total': 0}

            grid_distribution[level][action] += 1
            grid_distribution[level]['total'] += 1

        return grid_distribution

    @staticmethod
    def format_summary_report(results: Dict[str, Any]) -> str:
        """
        格式化文本摘要报告（阶段1）

        参数:
            results: 回测结果字典

        返回:
            str: 格式化的文本报告
        """
        report = []
        report.append("=" * 80)
        report.append("Grid Trading Strategy Backtest Results")
        report.append("=" * 80)
        report.append("")

        # 基本信息
        report.append(f"ETF Code: {results.get('etf_code', 'N/A')}")
        report.append(f"ETF Name: {results.get('etf_name', 'N/A')}")
        report.append("")

        # 收益指标
        report.append("Return Metrics:")
        report.append("-" * 40)
        report.append(f"Initial Cash: {results.get('initial_cash', 0):,.2f}")
        report.append(f"Final Value: {results.get('final_value', 0):,.2f}")
        report.append(f"Total Return: {results.get('total_return', 0):.2f}%")
        report.append(f"Total PnL: {results.get('total_pnl', 0):,.2f}")
        report.append("")

        # 网格效率指标
        report.append("Grid Efficiency Metrics:")
        report.append("-" * 40)
        report.append(f"Total Grid Triggers: {results.get('total_grid_triggers', 0)}")
        report.append(f"Buy Triggers: {results.get('buy_grid_triggers', 0)}")
        report.append(f"Sell Triggers: {results.get('sell_grid_triggers', 0)}")
        report.append(f"Trigger Frequency: {results.get('grid_trigger_frequency', 0):.2f} triggers/month")
        report.append(f"Unique Grids Used: {results.get('unique_grids_used', 0)}")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    @staticmethod
    def aggregate_multiple_results(
        individual_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        聚合多个策略的回测结果

        参数:
            individual_results: {etf_code: result_dict, ...}

        返回:
            Dict: 聚合后的汇总结果
        """
        if not individual_results:
            return {}

        # 计算汇总统计
        etf_codes = list(individual_results.keys())

        # 按收益率排序
        ranking = sorted(
            etf_codes,
            key=lambda code: individual_results[code].get('total_return', 0),
            reverse=True
        )

        best_performer = ranking[0] if ranking else None
        worst_performer = ranking[-1] if ranking else None

        # 汇总指标
        avg_return = np.mean([
            individual_results[code].get('total_return', 0)
            for code in etf_codes
        ])

        total_triggers = sum(
            individual_results[code].get('total_grid_triggers', 0)
            for code in etf_codes
        )

        aggregate = {
            'ranking': ranking,
            'best_performer': best_performer,
            'worst_performer': worst_performer,
            'average_return': round(avg_return, 2),
            'total_strategies': len(etf_codes),
            'total_triggers': total_triggers,
            'individual_results': individual_results,
        }

        return aggregate

    @staticmethod
    def format_aggregate_report(aggregate: Dict[str, Any]) -> str:
        """
        格式化聚合报告

        参数:
            aggregate: 聚合结果字典

        返回:
            str: 格式化的聚合报告
        """
        report = []
        report.append("=" * 80)
        report.append("Grid Trading Strategy Batch Backtest Summary")
        report.append("=" * 80)
        report.append("")

        report.append(f"Total Strategies Backtested: {aggregate.get('total_strategies', 0)}")
        report.append(f"Average Return: {aggregate.get('average_return', 0):.2f}%")
        report.append(f"Total Grid Triggers: {aggregate.get('total_triggers', 0)}")
        report.append("")

        report.append("Top 5 Performers:")
        report.append("-" * 80)
        ranking = aggregate.get('ranking', [])
        individual_results = aggregate.get('individual_results', {})

        for i, code in enumerate(ranking[:5], 1):
            result = individual_results.get(code, {})
            name = result.get('etf_name', 'N/A')
            ret = result.get('total_return', 0)
            triggers = result.get('total_grid_triggers', 0)

            report.append(f"{i}. {code} ({name}): {ret:+.2f}% ({triggers} triggers)")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


# 测试代码
if __name__ == "__main__":
    # 测试指标分析器
    test_grid_triggers = [
        {'date': '2024-01-05', 'action': 'buy', 'grid_level': 1, 'shares': 1000, 'amount': 1500},
        {'date': '2024-01-10', 'action': 'sell', 'grid_level': 1, 'shares': 1000, 'amount': 1600},
        {'date': '2024-01-15', 'action': 'buy', 'grid_level': 2, 'shares': 1000, 'amount': 1400},
    ]

    metrics = GridMetricsAnalyzer.calculate_basic_metrics(
        grid_triggers=test_grid_triggers,
        final_value=100200,
        initial_cash=100000,
        start_date='20240101',
        end_date='20241231'
    )

    print("Grid Metrics Test")
    print("=" * 80)
    print(GridMetricsAnalyzer.format_summary_report({'etf_code': '560590', 'etf_name': 'Test ETF', **metrics}))
