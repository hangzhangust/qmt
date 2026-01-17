# -*- coding: utf-8 -*-
"""
Quick Test Script - Validate Backtest System Basic Functions
快速测试脚本 - 验证回测系统基础功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_basic_imports():
    """Test 1: Basic module imports"""
    print("=" * 60)
    print("Test 1: Basic Module Imports / 测试 1: 基础模块导入")
    print("=" * 60)

    try:
        from backtesting.backtrader_engine import BacktestEngine
        from backtesting.all_weather_bt_strategy import AllWeatherStrategy
        from strategies.all_weather_strategy import AllWeatherStrategy as CoreAllWeatherStrategy
        from utils.config_loader import ConfigLoader
        print("[OK] All modules imported successfully")
        print("[OK] 所有模块导入成功")
        return True
    except Exception as e:
        print(f"[X] Module import failed: {e}")
        print(f"[X] 模块导入失败: {e}")
        return False


def test_config_loading():
    """Test 2: Configuration loading"""
    print("\n" + "=" * 60)
    print("Test 2: Configuration Loading / 测试 2: 配置加载")
    print("=" * 60)

    try:
        from utils.config_loader import ConfigLoader
        config = ConfigLoader.load_strategy_config()
        print(f"[OK] Configuration loaded successfully")
        print(f"[OK] 配置加载成功")
        print(f"     Position ratio: {config.get('all_weather_position_ratio', 0.5)*100:.1f}%")
        print(f"     仓位比例: {config.get('all_weather_position_ratio', 0.5)*100:.1f}%")
        print(f"     Rebalance period: {config.get('rebalance_period', 60)} days")
        print(f"     再平衡周期: {config.get('rebalance_period', 60)}天")
        return True
    except Exception as e:
        print(f"[X] Configuration loading failed: {e}")
        print(f"[X] 配置加载失败: {e}")
        return False


def test_strategy_initialization():
    """Test 3: Strategy initialization"""
    print("\n" + "=" * 60)
    print("Test 3: Strategy Initialization / 测试 3: 策略初始化")
    print("=" * 60)

    try:
        from strategies.all_weather_strategy import AllWeatherStrategy
        from utils.config_loader import ConfigLoader

        config = ConfigLoader.load_strategy_config()
        strategy = AllWeatherStrategy(config)

        etf_list = strategy.get_etf_universe()
        print(f"[OK] Strategy initialized successfully")
        print(f"[OK] 策略初始化成功")
        print(f"     ETF count: {len(etf_list)}")
        print(f"     ETF数量: {len(etf_list)}")
        return True
    except Exception as e:
        print(f"[X] Strategy initialization failed: {e}")
        print(f"[X] 策略初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtest_engine():
    """Test 4: Backtest engine"""
    print("\n" + "=" * 60)
    print("Test 4: Backtest Engine / 测试 4: 回测引擎")
    print("=" * 60)

    try:
        from backtesting.backtrader_engine import BacktestEngine

        engine = BacktestEngine(initial_cash=100000, commission=0.0001)
        print(f"[OK] Backtest engine created successfully")
        print(f"[OK] 回测引擎创建成功")
        print(f"     Initial cash: {engine.cerebro.broker.startingcash:,.2f}")
        print(f"     初始资金: {engine.cerebro.broker.startingcash:,.2f}")
        return True
    except Exception as e:
        print(f"[X] Backtest engine creation failed: {e}")
        print(f"[X] 回测引擎创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xtquant_connection():
    """Test 5: XtQuant connection"""
    print("\n" + "=" * 60)
    print("Test 5: XtQuant Connection / 测试 5: XtQuant连接")
    print("=" * 60)

    try:
        from xtquant import xtdata
        result = xtdata.connect()
        # Newer versions of xtquant return a client object when connected successfully
        # Use is_connected() method to verify the connection
        if result is not None and hasattr(result, 'is_connected') and result.is_connected():
            print(f"[OK] XtQuant connection successful")
            print(f"[OK] XtQuant连接成功")
            return True
        else:
            print(f"[X] XtQuant connection failed, result: {result}")
            print(f"[X] XtQuant连接失败，结果: {result}")
            return False
    except Exception as e:
        print(f"[X] XtQuant connection error: {e}")
        print(f"[X] XtQuant连接异常: {e}")
        return False


def main():
    """Main test function"""
    print("\n" + "*" * 60)
    print("*" + " " * 58 + "*")
    print("*" + "  Backtest System Quick Test".center(58) + "*")
    print("*" + "  回测系统快速测试".center(58) + "*")
    print("*" + " " * 58 + "*")
    print("*" * 60 + "\n")

    results = []
    results.append(("Basic Module Imports / 基础模块导入", test_basic_imports()))
    results.append(("Configuration Loading / 配置加载", test_config_loading()))
    results.append(("Strategy Initialization / 策略初始化", test_strategy_initialization()))
    results.append(("Backtest Engine / 回测引擎", test_backtest_engine()))
    results.append(("XtQuant Connection / XtQuant连接", test_xtquant_connection()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary / 测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[X]"
        print(f"{status} {name}")

    print(f"\nPassed / 通过: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Backtest system is ready to use.")
        print("[OK] 所有测试通过！回测系统可以正常使用。")
        print("\nNext step / 下一步: Run actual backtest")
        print("python run_backtest.py --start 20230101 --end 20231231")
        return 0
    else:
        print("\n[X] Some tests failed, please check the errors above.")
        print("[X] 部分测试失败，请检查上述错误。")
        print("\nRun environment check / 运行环境检查:")
        print("python setup_environment.py")
        return 1


if __name__ == '__main__':
    sys.exit(main())
