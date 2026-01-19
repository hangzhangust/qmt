# -*- coding: utf-8 -*-
"""
All-Weather Strategy Backtest Script
全天候策略回测执行脚本
使用Backtrader进行策略回测
"""
import argparse
import sys
import os

# Handle Windows encoding issues
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtrader_engine import BacktestEngine
from backtesting.all_weather_bt_strategy import AllWeatherStrategy
from strategies.all_weather_strategy import AllWeatherStrategy as CoreAllWeatherStrategy
from utils.config_loader import ConfigLoader


def main():
    """
    Main function / 主函数
    """
    # Environment check / 环境检查
    print("=" * 80)
    print("Environment Check / 环境检查...")
    print("=" * 80)

    # Check dependencies / 检查依赖
    try:
        import backtrader
        import xtquant
        import pandas
        import numpy
        import matplotlib
        print("[OK] All dependencies installed / 所有依赖已安装")
    except ImportError as e:
        print(f"[X] Missing dependency / 依赖缺失: {e}")
        print("\nPlease run / 请运行: pip install -r requirements.txt")
        return 1

    # Check XtQuant connection / 检查XtQuant连接
    try:
        from xtquant import xtdata
        connect_result = xtdata.connect()
        # Newer versions of xtquant return a client object when connected successfully
        # Use is_connected() method to verify the connection
        if connect_result is None or not hasattr(connect_result, 'is_connected') or not connect_result.is_connected():
            print(f"[X] XtQuant connection failed, result / XtQuant连接失败，结果: {connect_result}")
            print("Please check if XtQuant is running / 请检查XtQuant是否正常运行")
            return 1
        print("[OK] XtQuant connection successful / XtQuant连接成功")
    except Exception as e:
        print(f"[X] XtQuant connection error / XtQuant连接异常: {e}")
        return 1

    # Parse command line arguments / 解析命令行参数
    parser = argparse.ArgumentParser(
        description='All-Weather Strategy Backtest System / 全天候策略回测系统'
    )
    parser.add_argument('--start', required=True,
                        help='Start date (YYYYMMDD) / 开始日期 (YYYYMMDD)')
    parser.add_argument('--end', required=True,
                        help='End date (YYYYMMDD) / 结束日期 (YYYYMMDD)')
    parser.add_argument('--cash', type=float, default=1000000,
                        help='Initial cash (default: 1000000) / 初始资金 (默认1000000)')
    parser.add_argument('--position_ratio', type=float, default=None,
                        help='Position ratio (default: use config) / 仓位比例 (默认使用配置文件)')
    parser.add_argument('--rebalance_period', type=int, default=None,
                        help='Rebalance period in days (default: use config) / 再平衡周期(天) (默认使用配置文件)')
    parser.add_argument('--commission', type=float, default=0.0001,
                        help='Commission rate (default: 0.0001) / 手续费率 (默认0.0001)')
    parser.add_argument('--no_cache', action='store_true',
                        help='Disable data cache / 禁用数据缓存')

    # Visualization parameters / 可视化参数
    parser.add_argument('--plot', action='store_true',
                        help='Display visualization charts / 显示可视化图表')
    parser.add_argument('--save_plot', type=str, default=None,
                        help='Save chart path (e.g., results.png) / 保存图表路径 (如: results.png)')
    parser.add_argument('--show_metrics', action='store_true',
                        help='Show enhanced performance metrics / 显示增强性能指标')

    args = parser.parse_args()

    print("=" * 80)
    print("All-Weather Strategy Backtest System")
    print("全天候策略回测系统")
    print("=" * 80)

    # Load configuration / 加载配置
    print("\n1. Load Configuration / 加载配置...")
    config = ConfigLoader.load_strategy_config()

    # Override configuration parameters / 覆盖配置参数
    if args.position_ratio is not None:
        config['all_weather_position_ratio'] = args.position_ratio
    if args.rebalance_period is not None:
        config['rebalance_period'] = args.rebalance_period

    print(f"   Start date / 开始日期: {args.start}")
    print(f"   End date / 结束日期: {args.end}")
    print(f"   Initial cash / 初始资金: {args.cash:,.2f}")
    print(f"   Position ratio / 仓位比例: {config['all_weather_position_ratio']*100:.1f}%")
    print(f"   Rebalance period / 再平衡周期: {config['rebalance_period']}天")
    print(f"   Commission rate / 手续费率: {args.commission*100:.2f}%")
    print(f"   Use cache / 使用缓存: {'No' if args.no_cache else 'Yes'}")

    # Create core strategy instance / 创建核心策略实例
    print("\n2. Initialize Strategy / 初始化策略...")
    core_strategy = CoreAllWeatherStrategy(config)

    # Get ETF list / 获取ETF列表
    etf_codes = core_strategy.get_etf_universe()
    print(f"   ETF count / ETF数量: {len(etf_codes)}")
    print(f"   ETF list / ETF列表: {etf_codes}")

    # Create backtest engine / 创建回测引擎
    print("\n3. Initialize Backtest Engine / 初始化回测引擎...")
    engine = BacktestEngine(initial_cash=args.cash, commission=args.commission)

    # Add data feeds / 添加数据源
    print("\n4. Load Data / 加载数据...")
    use_cache = not args.no_cache

    # 使用智能数据加载（支持NaN填充未上市的ETF）
    listing_dates = engine.add_data_feeds_smart(
        stock_codes=etf_codes,
        start_date=args.start,
        end_date=args.end,
        period='1d',
        use_cache=use_cache
    )

    # 打印ETF上市日期用于验证
    print(f"\nETF上市日期:")
    for etf, date in sorted(listing_dates.items(), key=lambda x: x[1]):
        print(f"  {etf}: {date}")

    # Add strategy / 添加策略
    print("\n5. Add Strategy / 添加策略...")
    engine.add_strategy(
        AllWeatherStrategy,
        position_ratio=config['all_weather_position_ratio'],
        rebalance_period=config['rebalance_period'],
        etf_allocation=core_strategy.ALL_WEATHER_CONFIG,
        category_weights=core_strategy.get_category_weights(),
        listing_dates=listing_dates  # 传递上市日期信息
    )

    # Add analyzers / 添加分析器
    print("\n6. Add Analyzers / 添加分析器...")
    engine.add_analyzers()

    # Run backtest / 运行回测
    print("\n7. Run Backtest / 运行回测...")
    try:
        strategies = engine.run()

        # Get first strategy instance / 获取第一个策略实例
        if len(strategies) > 0:
            strategy = strategies[0]

            # Print results / 打印结果
            print("\n8. Backtest Results / 回测结果:")
            engine.print_results(strategy)

            # Show enhanced performance metrics / 显示增强性能指标
            if args.show_metrics:
                print("\n9. Enhanced Performance Metrics / 增强性能指标:")
                enhanced_metrics = engine.calculate_enhanced_metrics(strategy)
                print(f"   Total return / 总收益率: {enhanced_metrics['total_return']*100:.2f}%")
                print(f"   Annual return / 年化收益率: {enhanced_metrics['avg_annual_return']*100:.2f}%")
                print(f"   Excess return / 超额收益: {enhanced_metrics['excess_return']*100:.2f}% (基准: {enhanced_metrics['benchmark_return']*100:.1f}%)")
                print(f"   Sharpe ratio / 夏普比率: {enhanced_metrics['sharpe_ratio']:.4f}")
                print(f"   Sortino ratio / Sortino比率: {enhanced_metrics['sortino_ratio']:.4f}")
                print(f"   Max drawdown / 最大回撤: {enhanced_metrics['max_drawdown']:.2f}%")
                print(f"   Volatility / 波动率: {enhanced_metrics['volatility']:.2f}%")
                print(f"   Total trades / 总交易次数: {enhanced_metrics['total_trades']}")
                print(f"   Won trades / 盈利次数: {enhanced_metrics['won_trades']}")
                print(f"   Lost trades / 亏损次数: {enhanced_metrics['lost_trades']}")
                print(f"   Win rate / 胜率: {enhanced_metrics['win_rate']*100:.2f}%")

            # Visualization charts / 可视化图表
            if args.plot or args.save_plot:
                print("\n10. Generate Visualization Charts / 生成可视化图表...")
                # Determine whether to show chart / 确定是否显示图表
                show_plot = args.plot
                engine.plot_results(strategy, save_path=args.save_plot, show=show_plot)

            # Save results to file / 保存结果到文件
            save_results_to_file(strategy, args, config, enhanced_metrics if args.show_metrics else None)

        else:
            print("Backtest failed: No strategy instance / 回测失败：没有策略实例")

    except Exception as e:
        print(f"\nBacktest execution failed / 回测执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\nBacktest completed! / 回测完成!")
    return 0


def save_results_to_file(strategy, args, config, enhanced_metrics=None):
    """
    Save backtest results to file
    保存回测结果到文件

    Args:
        strategy: Strategy instance / 策略实例
        args: Command line arguments / 命令行参数
        config: Configuration dictionary / 配置字典
        enhanced_metrics: Enhanced performance metrics (optional) / 增强性能指标（可选）
    """
    try:
        import datetime

        # Generate filename / 生成文件名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = f"backtest_result_{timestamp}.txt"

        # Get results / 获取结果
        results = strategy.broker.getvalue()

        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("All-Weather Strategy Backtest Report\n")
            f.write("全天候策略回测报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Backtest time / 回测时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Backtest period / 回测区间: {args.start} - {args.end}\n")
            f.write(f"Initial cash / 初始资金: {args.cash:,.2f}\n")
            f.write(f"Final value / 最终资金: {results:,.2f}\n")
            f.write(f"Total return / 总收益率: {(results - args.cash) / args.cash * 100:.2f}%\n")
            f.write(f"Position ratio / 仓位比例: {config['all_weather_position_ratio']*100:.1f}%\n")
            f.write(f"Rebalance period / 再平衡周期: {config['rebalance_period']}天\n")

            # Write enhanced metrics if available / 如果有增强指标，写入文件
            if enhanced_metrics:
                f.write("\n" + "-" * 80 + "\n")
                f.write("Enhanced Performance Metrics / 增强性能指标\n")
                f.write("-" * 80 + "\n")
                f.write(f"Annual return / 年化收益率: {enhanced_metrics['avg_annual_return']*100:.2f}%\n")
                f.write(f"Excess return / 超额收益: {enhanced_metrics['excess_return']*100:.2f}% (基准: {enhanced_metrics['benchmark_return']*100:.1f}%)\n")
                f.write(f"Sharpe ratio / 夏普比率: {enhanced_metrics['sharpe_ratio']:.4f}\n")
                f.write(f"Sortino ratio / Sortino比率: {enhanced_metrics['sortino_ratio']:.4f}\n")
                f.write(f"Max drawdown / 最大回撤: {enhanced_metrics['max_drawdown']:.2f}%\n")
                f.write(f"Max drawdown duration / 最大回撤持续天数: {enhanced_metrics['max_drawdown_len']}天\n")
                f.write(f"Volatility / 波动率: {enhanced_metrics['volatility']:.2f}%\n")
                f.write(f"Total trades / 总交易次数: {enhanced_metrics['total_trades']}\n")
                f.write(f"Won trades / 盈利次数: {enhanced_metrics['won_trades']}\n")
                f.write(f"Lost trades / 亏损次数: {enhanced_metrics['lost_trades']}\n")
                f.write(f"Win rate / 胜率: {enhanced_metrics['win_rate']*100:.2f}%\n")

            f.write("\n" + "=" * 80 + "\n")

        print(f"Results saved to / 结果已保存到: {result_file}")

    except Exception as e:
        print(f"Failed to save results / 保存结果失败: {e}")


if __name__ == '__main__':
    sys.exit(main())
