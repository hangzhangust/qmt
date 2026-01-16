"""
全天候策略回测执行脚本
使用Backtrader进行策略回测
"""
import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtrader_engine import BacktestEngine
from backtesting.all_weather_bt_strategy import AllWeatherStrategy
from strategies.all_weather_strategy import AllWeatherStrategy as CoreAllWeatherStrategy
from utils.config_loader import ConfigLoader


def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='全天候策略回�?')
    parser.add_argument('--start', required=True, help='�?始日�? (YYYYMMDD)')
    parser.add_argument('--end', required=True, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--cash', type=float, default=1000000, help='初始资金 (默认1000000)')
    parser.add_argument('--position_ratio', type=float, default=None, help='仓位比例 (默认使用配置文件)')
    parser.add_argument('--rebalance_period', type=int, default=None, help='再平衡周�?(�?) (默认使用配置文件)')
    parser.add_argument('--commission', type=float, default=0.0001, help='手续费率 (默认0.0001)')
    parser.add_argument('--no_cache', action='store_true', help='禁用数据缓存')

    # 可视化参数
    parser.add_argument('--plot', action='store_true', help='显示可视化图表')
    parser.add_argument('--save_plot', type=str, default=None, help='保存图表路径 (如: results.png)')
    parser.add_argument('--show_metrics', action='store_true', help='显示增强性能指标')

    args = parser.parse_args()

    print("=" * 80)
    print("全天候策略回测系�?")
    print("=" * 80)

    # 加载配置
    print("\n1. 加载配置...")
    config = ConfigLoader.load_strategy_config()

    # 覆盖配置参数
    if args.position_ratio is not None:
        config['all_weather_position_ratio'] = args.position_ratio
    if args.rebalance_period is not None:
        config['rebalance_period'] = args.rebalance_period

    print(f"   开始日期: {args.start}")
    print(f"   结束日期: {args.end}")
    print(f"   初始资金: {args.cash:,.2f}")
    print(f"   仓位比例: {config['all_weather_position_ratio']*100:.1f}%")
    print(f"   再平衡周期: {config['rebalance_period']}天")
    print(f"   手续费率: {args.commission*100:.2f}%")
    print(f"   使用缓存: {'否' if args.no_cache else '是'}")

    # 创建核心策略实例
    print("\n2. 初始化策�?...")
    core_strategy = CoreAllWeatherStrategy(config)

    # 获取ETF列表
    etf_codes = core_strategy.get_etf_universe()
    print(f"   ETF数量: {len(etf_codes)}")
    print(f"   ETF列表: {etf_codes}")

    # 创建回测引擎
    print("\n3. 初始化回测引�?...")
    engine = BacktestEngine(initial_cash=args.cash, commission=args.commission)

    # 添加数据�?
    print("\n4. 加载数据�?...")
    use_cache = not args.no_cache
    engine.add_data_feeds(
        stock_codes=etf_codes,
        start_date=args.start,
        end_date=args.end,
        period='1d',
        use_cache=use_cache
    )

    # 添加策略
    print("\n5. 添加策略...")
    engine.add_strategy(
        AllWeatherStrategy,
        position_ratio=config['all_weather_position_ratio'],
        rebalance_period=config['rebalance_period'],
        etf_allocation=core_strategy.ALL_WEATHER_CONFIG,
        category_weights=core_strategy.get_category_weights()
    )

    # 添加分析�?
    print("\n6. 添加分析�?...")
    engine.add_analyzers()

    # 运行回测
    print("\n7. 运行回测...")
    try:
        strategies = engine.run()

        # 获取第一个策略实�?
        if len(strategies) > 0:
            strategy = strategies[0]

            # 打印结果
            print("\n8. 回测结果:")
            engine.print_results(strategy)

            # 显示增强性能指标
            if args.show_metrics:
                print("\n9. 增强性能指标:")
                enhanced_metrics = engine.calculate_enhanced_metrics(strategy)
                print(f"   总收益率: {enhanced_metrics['total_return']*100:.2f}%")
                print(f"   年化收益率: {enhanced_metrics['avg_annual_return']*100:.2f}%")
                print(f"   夏普比率: {enhanced_metrics['sharpe_ratio']:.4f}")
                print(f"   Sortino比率: {enhanced_metrics['sortino_ratio']:.4f}")
                print(f"   最大回撤: {enhanced_metrics['max_drawdown']:.2f}%")
                print(f"   波动率: {enhanced_metrics['volatility']:.2f}%")
                print(f"   总交易次数: {enhanced_metrics['total_trades']}")
                print(f"   盈利次数: {enhanced_metrics['won_trades']}")
                print(f"   亏损次数: {enhanced_metrics['lost_trades']}")
                print(f"   胜率: {enhanced_metrics['win_rate']*100:.2f}%")

            # 可视化图表
            if args.plot or args.save_plot:
                print("\n10. 生成可视化图表...")
                # 确定是否显示图表
                show_plot = args.plot
                engine.plot_results(strategy, save_path=args.save_plot, show=show_plot)

            # 保存结果到文件
            save_results_to_file(strategy, args, config, enhanced_metrics if args.show_metrics else None)

        else:
            print("回测失败：没有策略实例")

    except Exception as e:
        print(f"\n回测执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n回测完成!")
    return 0


def save_results_to_file(strategy, args, config, enhanced_metrics=None):
    """
    保存回测结果到文件

    参数:
        strategy: 策略实例
        args: 命令行参数
        config: 配置字典
        enhanced_metrics: 增强性能指标（可选）
    """
    try:
        import datetime

        # 生成文件名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = f"backtest_result_{timestamp}.txt"

        # 获取结果
        results = strategy.broker.getvalue()

        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("All-Weather Strategy Backtest Report\n")
            f.write("全天候策略回测报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"回测时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"回测区间: {args.start} - {args.end}\n")
            f.write(f"初始资金: {args.cash:,.2f}\n")
            f.write(f"最终资金: {results:,.2f}\n")
            f.write(f"总收益率: {(results - args.cash) / args.cash * 100:.2f}%\n")
            f.write(f"仓位比例: {config['all_weather_position_ratio']*100:.1f}%\n")
            f.write(f"再平衡周期: {config['rebalance_period']}天\n")

            # 如果有增强指标，写入文件
            if enhanced_metrics:
                f.write("\n" + "-" * 80 + "\n")
                f.write("增强性能指标 / Enhanced Performance Metrics\n")
                f.write("-" * 80 + "\n")
                f.write(f"年化收益率: {enhanced_metrics['avg_annual_return']*100:.2f}%\n")
                f.write(f"夏普比率: {enhanced_metrics['sharpe_ratio']:.4f}\n")
                f.write(f"Sortino比率: {enhanced_metrics['sortino_ratio']:.4f}\n")
                f.write(f"最大回撤: {enhanced_metrics['max_drawdown']:.2f}%\n")
                f.write(f"最大回撤持续天数: {enhanced_metrics['max_drawdown_len']}天\n")
                f.write(f"波动率: {enhanced_metrics['volatility']:.2f}%\n")
                f.write(f"总交易次数: {enhanced_metrics['total_trades']}\n")
                f.write(f"盈利次数: {enhanced_metrics['won_trades']}\n")
                f.write(f"亏损次数: {enhanced_metrics['lost_trades']}\n")
                f.write(f"胜率: {enhanced_metrics['win_rate']*100:.2f}%\n")

            f.write("\n" + "=" * 80 + "\n")

        print(f"结果已保存到: {result_file}")

    except Exception as e:
        print(f"保存结果失败: {e}")


if __name__ == '__main__':
    sys.exit(main())
