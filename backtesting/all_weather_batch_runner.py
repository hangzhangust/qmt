# encoding:utf-8
"""
全天候策略批量回测引擎
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtrader_engine import BacktestEngine
from backtesting.all_weather_bt_strategy import AllWeatherStrategy
from typing import Dict, Any
import pandas as pd


class AllWeatherBatchRunner:
    """全天候策略回测运行器"""

    def __init__(self, initial_cash: float = 1000000):
        """
        初始化回测运行器

        参数:
            initial_cash: 初始资金
        """
        self.initial_cash = initial_cash

    def run_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行全天候策略回测

        参数:
            config: {
                'position_ratio': float,          # 仓位比例
                'rebalance_period': int,          # 再平衡周期(天)
                'rebalance_threshold': float,     # 再平衡阈值
                'custom_allocation': dict,        # 可选：自定义资产配置
                'start_date': str,                # 回测开始日期 (YYYYMMDD)
                'end_date': str                   # 回测结束日期 (YYYYMMDD)
            }

        返回:
            回测结果字典
        """
        try:
            print(f"\n{'='*60}")
            print(f"全天候策略回测启动")
            print(f"{'='*60}")

            # 1. 准备ETF配置
            print(f"准备ETF资产配置...")
            etf_allocation = self._prepare_etf_allocation(config.get('custom_allocation'))

            # 打印配置信息
            for category, alloc_config in etf_allocation.items():
                print(f"  - {category}: {alloc_config['names']}")

            # 2. 创建回测引擎
            print(f"\n创建回测引擎 (初始资金: ¥{self.initial_cash:,.0f})...")
            engine = BacktestEngine(initial_cash=self.initial_cash)

            # 3. 加载ETF数据（使用智能添加，处理未上市ETF）
            print(f"加载ETF数据 ({config['start_date']} - {config['end_date']})...")
            stock_codes = self._extract_stock_codes(etf_allocation)
            print(f"  ETF代码列表: {', '.join(stock_codes)}")

            engine.add_data_feeds_smart(stock_codes, config['start_date'], config['end_date'])

            # 4. 添加策略
            print(f"\n添加全天候策略...")
            strategy_params = {
                'position_ratio': config.get('position_ratio', 0.5),
                'rebalance_period': config.get('rebalance_period', 60),
                'rebalance_threshold': config.get('rebalance_threshold', 0.05),
                'etf_allocation': etf_allocation,
                'category_weights': {
                    'commodities': 0.25,
                    'stocks': 0.25,
                    'long_bonds': 0.25,
                    'short_bonds': 0.25
                }
            }

            print(f"  - 仓位比例: {strategy_params['position_ratio']*100:.0f}%")
            print(f"  - 再平衡周期: {strategy_params['rebalance_period']}天")
            print(f"  - 再平衡阈值: {strategy_params['rebalance_threshold']*100:.0f}%")

            engine.add_strategy(AllWeatherStrategy, **strategy_params)

            # 5. 运行回测
            print(f"\n开始执行回测...")
            results = engine.run()

            # 6. 提取结果
            print(f"\n提取回测结果...")
            result = self._extract_results(results, strategy_params)

            # 打印结果摘要
            print(f"\n{'='*60}")
            print(f"回测完成")
            print(f"{'='*60}")
            print(f"初始资金: ¥{result['initial_cash']:,.0f}")
            print(f"最终价值: ¥{result['final_value']:,.0f}")
            print(f"总收益率: {result['total_return']:.2f}%")
            print(f"再平衡次数: {result['rebalance_count']}")
            print(f"{'='*60}\n")

            return result

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()

            print(f"\n{'='*60}")
            print(f"回测失败")
            print(f"{'='*60}")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print(f"{'='*60}\n")

            return {
                'error': str(e),
                'initial_cash': self.initial_cash,
                'final_value': self.initial_cash,
                'total_return': 0.0,
                'rebalance_count': 0,
                'rebalance_history': [],
                'traceback': error_details
            }

    def _prepare_etf_allocation(self, custom_alloc: Dict = None) -> Dict:
        """
        准备ETF资产配置

        参数:
            custom_alloc: 自定义资产配置（可选）

        返回:
            ETF配置字典
        """
        if custom_alloc:
            return custom_alloc

        # 默认配置（四类资产等权25%）
        return {
            'commodities': {
                'target_weight': 0.25,
                'etfs': ['518880.SH'],
                'names': {'518880.SH': '黄金ETF'}
            },
            'stocks': {
                'target_weight': 0.25,
                'etfs': ['159915.SZ', '513100.SH', '513520.SH'],
                'names': {
                    '159915.SZ': '创业板ETF',
                    '513100.SH': '纳斯达克ETF',
                    '513520.SH': '日经ETF'
                }
            },
            'long_bonds': {
                'target_weight': 0.25,
                'etfs': ['511260.SH', '511010.SH'],
                'names': {
                    '511260.SH': '十年国债',
                    '511010.SH': '长债ETF'
                }
            },
            'short_bonds': {
                'target_weight': 0.25,
                'etfs': ['511360.SH'],
                'names': {'511360.SH': '短债ETF'}
            }
        }

    def _extract_stock_codes(self, etf_allocation: Dict) -> list:
        """
        提取所有ETF代码

        参数:
            etf_allocation: ETF配置字典

        返回:
            ETF代码列表
        """
        codes = []
        for category_config in etf_allocation.values():
            codes.extend(category_config['etfs'])
        return codes

    def _extract_results(self, cerebro_result: tuple, strategy_params: Dict) -> Dict[str, Any]:
        """
        提取回测结果

        参数:
            cerebro_result: Backtrader回测结果
            strategy_params: 策略参数

        返回:
            结果字典
        """
        strategy = cerebro_result[0]

        # 基础指标
        final_value = strategy.broker.getvalue()
        total_return = (final_value / self.initial_cash - 1) * 100

        # 全天候特定指标
        result = {
            'final_value': final_value,
            'initial_cash': self.initial_cash,
            'total_return': total_return,
            'rebalance_count': strategy.rebalance_counter,
            'rebalance_history': strategy.rebalance_dates,
            'strategy_params': strategy_params,
            'category_returns': {},  # 各类别收益
            'final_allocation': {}   # 最终资产配置
        }

        # TODO: 添加更多分析指标
        # - 最大回撤
        # - 夏普比率
        # - 各类别收益贡献
        # - 再平衡分析

        return result


if __name__ == '__main__':
    # 测试代码
    print("全天候策略回测引擎 - 测试运行\n")

    config = {
        'position_ratio': 0.5,
        'rebalance_period': 60,
        'rebalance_threshold': 0.05,
        'start_date': '20240101',
        'end_date': '20260121'
    }

    runner = AllWeatherBatchRunner(initial_cash=1000000)
    result = runner.run_backtest(config)

    if 'error' not in result:
        print(f"\n回测成功!")
        print(f"收益率: {result['total_return']:.2f}%")
        print(f"再平衡次数: {result['rebalance_count']}")
    else:
        print(f"\n回测失败: {result['error']}")
