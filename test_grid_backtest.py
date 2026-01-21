# -*- coding: utf-8 -*-
"""
网格交易策略回测系统测试脚本
测试阶段1的所有模块集成
"""
import sys
import os

# 处理Windows编码问题
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.grid_config_parser import GridConfigParser
from backtesting.grid_batch_runner import GridBatchRunner
from backtesting.grid_metrics import GridMetricsAnalyzer


def test_config_parser():
    """测试1：配置解析器"""
    print("\n" + "=" * 80)
    print("TEST 1: Configuration Parser")
    print("=" * 80)

    try:
        parser = GridConfigParser()
        configs = parser.parse_table_xls("Table.xls")

        print(f"✓ Successfully parsed {len(configs)} configurations")

        # 验证配置
        valid_count = 0
        for config in configs:
            if parser.validate_config(config):
                valid_count += 1

        print(f"✓ {valid_count}/{len(configs)} configurations are valid")

        # 显示第一个配置
        if configs:
            print(f"\nFirst configuration (560590):")
            config = configs[0]
            print(f"  ETF Code: {config['etf_code']}")
            print(f"  ETF Name: {config['etf_name']}")
            print(f"  Base Price: {config['base_price']}")
            print(f"  Grid Spacing: +{config['grid_spacing_up']}% / {config['grid_spacing_down']}%")
            print(f"  Buy Amount: {config['buy_amount']} {config['buy_amount_type']}")
            print(f"  Sell Amount: {config['sell_amount']} {config['sell_amount_type']}")

        return configs, True

    except Exception as e:
        print(f"✗ Config parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def test_single_backtest(config):
    """测试2：单个策略回测"""
    print("\n" + "=" * 80)
    print("TEST 2: Single Strategy Backtest")
    print("=" * 80)

    try:
        # 使用较小的初始资金和较短时间进行快速测试
        runner = GridBatchRunner(
            start_date="20240101",
            end_date="20240331",  # 只测试3个月
            initial_cash=100000  # 10万初始资金
        )

        result = runner.run_single_backtest(config)

        if 'error' in result:
            print(f"✗ Backtest failed with error: {result['error']}")
            return None, False

        print(f"✓ Single backtest completed successfully")
        print(f"  Final Value: {result['final_value']:,.2f}")
        print(f"  Total Return: {result['total_return']:.2f}%")
        print(f"  Grid Triggers: {result['total_grid_triggers']}")

        return result, True

    except Exception as e:
        print(f"✗ Single backtest test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def test_batch_backtest(configs, max_strategies=3):
    """测试3：批量回测（限制策略数量）"""
    print("\n" + "=" * 80)
    print(f"TEST 3: Batch Backtest (First {max_strategies} strategies)")
    print("=" * 80)

    try:
        runner = GridBatchRunner(
            start_date="20240101",
            end_date="20240331",  # 只测试3个月
            initial_cash=100000
        )

        # 只测试前几个策略
        test_configs = configs[:max_strategies]

        # 创建临时输出目录
        output_dir = "test_results"
        aggregate = runner.run_batch_backtest(
            configs=test_configs,
            parallel=False,
            output_dir=output_dir
        )

        print(f"\n✓ Batch backtest completed successfully")
        print(f"  Average Return: {aggregate['average_return']:.2f}%")
        print(f"  Best Performer: {aggregate['best_performer']}")
        print(f"  Results exported to: {output_dir}/")

        return aggregate, True

    except Exception as e:
        print(f"✗ Batch backtest test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def main():
    """主测试函数"""
    print("=" * 80)
    print("Grid Trading Backtest System - Integration Test")
    print("=" * 80)

    # 测试1：配置解析
    configs, test1_pass = test_config_parser()
    if not test1_pass:
        print("\n✗ Test 1 FAILED - Cannot proceed without valid configurations")
        return False

    # 测试2：单个策略回测
    result, test2_pass = test_single_backtest(configs[0])
    if not test2_pass:
        print("\n⚠ Test 2 FAILED - Continuing with caution")

    # 测试3：批量回测
    aggregate, test3_pass = test_batch_backtest(configs, max_strategies=3)
    if not test3_pass:
        print("\n⚠ Test 3 FAILED - Batch backtest has issues")

    # 汇总结果
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Config Parser): {'✓ PASS' if test1_pass else '✗ FAIL'}")
    print(f"Test 2 (Single Backtest): {'✓ PASS' if test2_pass else '✗ FAIL'}")
    print(f"Test 3 (Batch Backtest): {'✓ PASS' if test3_pass else '✗ FAIL'}")
    print("=" * 80)

    all_pass = test1_pass and test2_pass and test3_pass

    if all_pass:
        print("\n✓ ALL TESTS PASSED - System is ready for production use!")
        print("\nNext steps:")
        print("  1. Run full backtest for all 17 strategies:")
        print("     python test_grid_backtest.py --full")
        print("  2. Or proceed to Phase 2 (Parameter Optimization, Visualization)")
        return True
    else:
        print("\n⚠ SOME TESTS FAILED - Please review and fix issues")
        return False


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description='Test Grid Trading Backtest System')
    parser.add_argument('--full', action='store_true',
                       help='Run full backtest for all 17 strategies (2 years)')

    args = parser.parse_args()

    if args.full:
        print("\nRunning FULL backtest for all 17 strategies (2024-01-01 to 2026-01-21)...")
        print("This may take 30-60 minutes...\n")

        # 加载配置
        config_parser = GridConfigParser()
        configs = config_parser.parse_table_xls("Table.xls")

        # 运行完整批量回测
        runner = GridBatchRunner(
            start_date="20240101",
            end_date="20260121",
            initial_cash=1000000  # 100万初始资金
        )

        output_dir = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        aggregate = runner.run_batch_backtest(
            configs=configs,
            parallel=False,
            output_dir=output_dir
        )

        print(f"\n✓ Full backtest completed!")
        print(f"  Results saved to: {output_dir}/")
        print(f"  Summary report: {output_dir}/batch_backtest_report.txt")
        print(f"  Summary CSV: {output_dir}/summary.csv")
    else:
        # 运行集成测试
        success = main()
        sys.exit(0 if success else 1)
