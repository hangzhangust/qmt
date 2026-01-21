# encoding:utf-8
"""
网格交易策略批量回测引擎
协调单个和多个网格策略的回测执行
"""
import backtrader as bt
import pandas as pd
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.grid_bt_strategy import GridTradingStrategy
from backtesting.grid_metrics import GridMetricsAnalyzer
from backtesting.backtrader_engine import XtDataPandasFeed
from strategies.grid_config_parser import GridConfigParser


class GridBatchRunner:
    """
    网格交易策略批量回测引擎

    支持单个和批量策略回测，结果导出和报告生成
    """

    def __init__(self, start_date: str, end_date: str, initial_cash: float = 1000000):
        """
        初始化批量回测引擎

        参数:
            start_date: 回测开始日期 (YYYYMMDD)
            end_date: 回测结束日期 (YYYYMMDD)
            initial_cash: 初始资金
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash

    def run_single_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行单个网格策略回测

        参数:
            config: 网格策略配置字典

        返回:
            Dict: 回测结果
        """
        etf_code = config['etf_code']

        print(f"\n{'=' * 80}")
        print(f"Running backtest for {etf_code} ({config['etf_name']})")
        print(f"{'=' * 80}")

        try:
            # 创建Cerebro引擎
            cerebro = bt.Cerebro()

            # 设置初始资金
            cerebro.broker.setcash(self.initial_cash)

            # 设置手续费（万分之1）
            cerebro.broker.setcommission(commission=0.0001)

            # 添加数据源
            data_feed = XtDataPandasFeed.from_xtdata(
                stock_code=etf_code,
                start_date=self.start_date,
                end_date=self.end_date,
                period='1d',
                use_cache=True
            )

            if data_feed is None:
                raise ValueError(f"Failed to load data for {etf_code}")

            cerebro.adddata(data_feed)

            # 添加策略
            cerebro.addstrategy(
                GridTradingStrategy,
                base_price=config['base_price'],
                grid_spacing_up=config['grid_spacing_up'],
                grid_spacing_down=config['grid_spacing_down'],
                buy_amount=config['buy_amount'],
                sell_amount=config['sell_amount'],
                buy_amount_type=config['buy_amount_type'],
                sell_amount_type=config['sell_amount_type'],
                max_grids=10,
                printlog=False,  # 关闭详细日志
            )

            # 添加分析器（添加错误处理）
            try:
                cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            except:
                pass  # 如果数据不足，跳过Sharpe分析器

            try:
                cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            except:
                pass  # 如果数据不足，跳过DrawDown分析器

            try:
                cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            except:
                pass  # 如果数据不足，跳过Returns分析器

            try:
                cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            except:
                pass  # 如果数据不足，跳过Trade分析器

            # 运行回测
            print(f"Starting backtest...")
            strategies = cerebro.run()
            strategy = strategies[0]

            # 获取分析结果
            strat = strategy

            # 最终资产价值
            final_value = cerebro.broker.getvalue()

            # 获取网格触发历史
            grid_triggers = strat.get_grid_triggers()

            # 获取绩效摘要
            performance_summary = strat.get_performance_summary()

            # 计算基础指标
            metrics = GridMetricsAnalyzer.calculate_basic_metrics(
                grid_triggers=grid_triggers,
                final_value=final_value,
                initial_cash=self.initial_cash,
                start_date=self.start_date,
                end_date=self.end_date
            )

            # 构建结果字典
            result = {
                'etf_code': config['etf_code'],
                'etf_name': config['etf_name'],
                'final_value': final_value,
                'grid_triggers': grid_triggers,
                'performance_summary': performance_summary,
                **metrics,
                'config': config,
            }

            print(f"Backtest completed successfully")
            print(f"Final Value: {final_value:,.2f}")
            print(f"Total Return: {metrics['total_return']:.2f}%")
            print(f"Grid Triggers: {metrics['total_grid_triggers']}")

            return result

        except Exception as e:
            print(f"ERROR: Backtest failed for {etf_code}: {e}")
            import traceback
            traceback.print_exc()

            # 返回错误结果
            return {
                'etf_code': etf_code,
                'etf_name': config.get('etf_name', 'Unknown'),
                'error': str(e),
                'final_value': self.initial_cash,
                'total_return': 0.0,
                'grid_triggers': [],
            }

    def run_batch_backtest(
        self,
        configs: List[Dict[str, Any]],
        parallel: bool = False,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量回测所有网格策略

        参数:
            configs: 17个策略配置列表
            parallel: 是否并行执行（阶段1暂不支持）
            output_dir: 结果输出目录

        返回:
            Dict: 批量回测汇总结果
        """
        print(f"\n{'=' * 80}")
        print(f"Grid Trading Strategy Batch Backtest")
        print(f"{'=' * 80}")
        print(f"Start Date: {self.start_date}")
        print(f"End Date: {self.end_date}")
        print(f"Initial Cash: {self.initial_cash:,.2f}")
        print(f"Total Strategies: {len(configs)}")
        print(f"{'=' * 80}\n")

        if parallel:
            print("WARNING: Parallel execution not yet supported, running sequentially")

        # 执行所有回测
        individual_results = {}

        for i, config in enumerate(configs, 1):
            print(f"\n[{i}/{len(configs)}] Processing {config['etf_code']}...")

            result = self.run_single_backtest(config)
            individual_results[config['etf_code']] = result

        # 聚合结果
        aggregate = GridMetricsAnalyzer.aggregate_multiple_results(individual_results)

        # 生成报告
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self.export_to_csv(individual_results, aggregate, output_dir)

            report_path = os.path.join(output_dir, 'batch_backtest_report.txt')
            self.generate_text_report(aggregate, report_path)

        print(f"\n{'=' * 80}")
        print(f"Batch backtest completed!")
        print(f"{'=' * 80}\n")

        # 打印汇总报告
        print(GridMetricsAnalyzer.format_aggregate_report(aggregate))

        return aggregate

    def export_to_csv(
        self,
        individual_results: Dict[str, Dict[str, Any]],
        aggregate: Dict[str, Any],
        output_dir: str
    ):
        """
        导出结果到CSV文件

        参数:
            individual_results: 单个策略结果字典
            aggregate: 聚合结果
            output_dir: 输出目录
        """
        print(f"\nExporting results to {output_dir}...")

        # 1. 导出汇总指标
        summary_data = []
        for etf_code, result in individual_results.items():
            if 'error' not in result and 'total_return' in result:
                summary_data.append({
                    'ETF_Code': result['etf_code'],
                    'ETF_Name': result['etf_name'],
                    'Total_Return_%': result.get('total_return', 0),
                    'Final_Value': result.get('final_value', 0),
                    'Total_PnL': result.get('total_pnl', 0),
                    'Total_Grid_Triggers': result.get('total_grid_triggers', 0),
                    'Buy_Triggers': result.get('buy_grid_triggers', 0),
                    'Sell_Triggers': result.get('sell_grid_triggers', 0),
                    'Trigger_Freq_Per_Month': result.get('grid_trigger_frequency', 0),
                })

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            # 安全地排序
            if 'Total_Return_%' in summary_df.columns:
                summary_df = summary_df.sort_values('Total_Return_%', ascending=False)

            summary_path = os.path.join(output_dir, 'summary.csv')
            summary_df.to_csv(summary_path, index=False, encoding='utf-8-sig')
            print(f"  - Summary: {summary_path}")
        else:
            print("  - No valid results to export in summary")

        # 2. 导出每个策略的网格触发历史
        for etf_code, result in individual_results.items():
            if 'error' not in result and result['grid_triggers']:
                triggers_df = pd.DataFrame(result['grid_triggers'])
                triggers_path = os.path.join(output_dir, f'grid_triggers_{etf_code}.csv')
                triggers_df.to_csv(triggers_path, index=False, encoding='utf-8-sig')

        print(f"  - Grid triggers: {len([r for r in individual_results.values() if r.get('grid_triggers')])} files")

        print("CSV export completed")

    def generate_text_report(self, aggregate: Dict[str, Any], report_path: str):
        """
        生成文本摘要报告

        参数:
            aggregate: 聚合结果
            report_path: 报告文件路径
        """
        report_content = GridMetricsAnalyzer.format_aggregate_report(aggregate)

        # 添加详细信息
        report_content += "\n\nDetailed Results:\n"
        report_content += "=" * 80 + "\n"

        ranking = aggregate.get('ranking', [])
        individual_results = aggregate.get('individual_results', {})

        for code in ranking:
            result = individual_results.get(code, {})
            if 'error' not in result:
                report_content += f"\n{code} ({result.get('etf_name', 'N/A')})\n"
                report_content += "-" * 80 + "\n"
                report_content += GridMetricsAnalyzer.format_summary_report(result)
                report_content += "\n"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"Text report: {report_path}")


# 测试代码
if __name__ == "__main__":
    # 测试批量回测引擎
    print("Grid Batch Runner Test")
    print("=" * 80)

    # 加载配置
    parser = GridConfigParser()
    configs = parser.parse_table_xls("Table.xls")

    if configs:
        print(f"Loaded {len(configs)} configurations")

        # 只测试第一个配置
        runner = GridBatchRunner(
            start_date="20240101",
            end_date="20260121",
            initial_cash=100000
        )

        # 运行单个回测
        result = runner.run_single_backtest(configs[0])

        print("\n" + "=" * 80)
        print("Test Result:")
        print(GridMetricsAnalyzer.format_summary_report(result))
