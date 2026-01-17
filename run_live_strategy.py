# -*- coding: utf-8 -*-
"""
All-Weather Strategy Live Trading Script
Program entry point, responsible for initializing and running live strategy
"""
import argparse
import sys
import os
import signal

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.all_weather_strategy import AllWeatherStrategy
from execution.xt_trader import XtTrader
from execution.live_engine import LiveTradingEngine
from data.xtdata_feed import XtDataFeed
from utils.config_loader import ConfigLoader


# 全局变量（用于信号处理）
engine = None


def signal_handler(signum, frame):
    """
    信号处理函数（Ctrl+C）
    """
    global engine
    print(f"\n收到信号 {signum}，正在停止策略...")
    if engine:
        engine.stop()
    sys.exit(0)


def parse_args():
    """
    解析命令行参数

    返回:
        argparse.Namespace: 参数对象
    """
    parser = argparse.ArgumentParser(
        description='全天候策略实盘执行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 实盘模式
  python run_live_strategy.py --mode live --strategy all_weather

  # 测试模式（不实际下单）
  python run_live_strategy.py --mode test --dry_run

  # 指定执行间隔（秒）
  python run_live_strategy.py --mode live --interval 120

  # 后台运行
  python run_live_strategy.py --mode live --daemon
        """
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['live', 'test'],
        default='live',
        help='运行模式: live=实盘, test=测试（默认: live）'
    )

    parser.add_argument(
        '--strategy',
        type=str,
        default='all_weather',
        help='策略名称（默认: all_weather）'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='执行间隔（秒），默认60秒'
    )

    parser.add_argument(
        '--dry_run',
        action='store_true',
        help='模拟运行，不实际下单（测试用）'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='只执行一次，不进入循环'
    )

    parser.add_argument(
        '--account_id',
        type=str,
        default=None,
        help='账户ID（默认从配置文件读取）'
    )

    parser.add_argument(
        '--session_id',
        type=int,
        default=None,
        help='会话ID（默认从配置文件读取）'
    )

    parser.add_argument(
        '--no_cache',
        action='store_true',
        help='禁用数据缓存'
    )

    return parser.parse_args()


def print_banner(config: dict, mode: str):
    """
    打印欢迎横幅

    参数:
        config: 配置字典
        mode: 运行模式
    """
    print("=" * 80)
    print("全天候策略实盘交易系统")
    print("=" * 80)
    print(f"运行模式: {mode.upper()}")
    print(f"策略名称: 全天候资产配置策略")
    print(f"仓位比例: {config.get('all_weather_position_ratio', 0.5) * 100:.1f}%")
    print(f"再平衡周期: {config.get('rebalance_period', 60)}天")
    print(f"执行间隔: {sys.argv[sys.argv.index('--interval') + 1] if '--interval' in sys.argv else 60}秒")
    print("=" * 80)
    print()


def validate_live_trading_setup(config: dict, mode: str, dry_run: bool) -> bool:
    """
    验证实盘交易设置

    参数:
        config: 配置字典
        mode: 运行模式
        dry_run: 是否为模拟运行

    返回:
        bool: 验证是否通过
    """
    print("\n实盘交易设置验证 / Live Trading Setup Validation")
    print("-" * 80)

    all_ok = True

    # 1. Check XtQuant connection
    print("\n1. 检查 XtQuant 数据连接 / Checking XtQuant Data Connection...")
    try:
        from xtquant import xtdata
        result = xtdata.get_full_tick(['000001.SZ'])
        if result is not None:
            print("   [OK] XtQuant 数据连接正常 / XtQuant Data Connected")
        else:
            print("   [X] XtQuant 数据连接失败 / XtQuant Data Connection Failed")
            print("   请确保 MiniQMT 客户端正在运行 / Please ensure MiniQMT client is running")
            all_ok = False
    except Exception as e:
        print(f"   [X] XtQuant 连接异常 / XtQuant Connection Error: {e}")
        all_ok = False

    # 2. Validate configuration
    print("\n2. 验证配置参数 / Validating Configuration...")
    required_configs = {
        'xtquant_account_id': '账户ID / Account ID',
        'xtquant_session_id': '会话ID / Session ID',
    }

    missing_configs = []
    for cfg, desc in required_configs.items():
        if not config.get(cfg):
            print(f"   [X] 缺少配置 / Missing Config: {cfg} ({desc})")
            missing_configs.append(cfg)

    if missing_configs:
        print(f"   请运行设置向导配置以上参数 / Please run setup wizard to configure above parameters:")
        print(f"   python setup_live_trading.py")
        all_ok = False
    else:
        account_id = config['xtquant_account_id']
        session_id = config['xtquant_session_id']
        print(f"   [OK] 账户ID / Account ID: {account_id}")
        print(f"   [OK] 会话ID / Session ID: {session_id}")

        # Validate account ID format
        if '.' not in account_id:
            print(f"   [WARNING] 账户ID格式可能不正确（应包含.SH或.SZ后缀）")
            print(f"   [WARNING] Account ID format may be incorrect (should include .SH or .SZ suffix)")
        else:
            market = account_id.split('.')[-1]
            if market in ['SH', 'SZ']:
                print(f"   [OK] 市场 / Market: {market}")
            else:
                print(f"   [X] 无效的市场后缀 / Invalid market suffix: {market}")
                all_ok = False

    # 3. For live mode (not dry-run), test trader connection
    if mode == 'live' and not dry_run and all_ok:
        print("\n3. 测试交易接口连接 / Testing Trading Interface Connection...")
        try:
            from execution.xt_trader import XtTrader

            trader = XtTrader(
                xtquant_path=config.get('xtquant_path', ''),
                account_id=config['xtquant_account_id'],
                session_id=config['xtquant_session_id']
            )

            if trader.connect():
                print("   [OK] 交易接口连接成功 / Trading Interface Connected")

                # Query account
                account_info = trader.query_account()
                if account_info:
                    print(f"   [OK] 账户查询成功 / Account Query Successful")
                    print(f"       总资产 / Total Asset: {account_info['total_asset']:,.2f}")
                    print(f"       可用资金 / Cash: {account_info['cash']:,.2f}")
                else:
                    print("   [X] 账户查询失败 / Account Query Failed")
                    all_ok = False

                trader.disconnect()
            else:
                print("   [X] 交易接口连接失败 / Trading Interface Connection Failed")
                print("   请检查账户ID和会话ID是否正确 / Please check if account ID and session ID are correct")
                all_ok = False

        except Exception as e:
            print(f"   [X] 交易接口测试失败 / Trading Interface Test Failed: {e}")
            all_ok = False

    print("\n" + "-" * 80)
    if all_ok:
        print("[OK] 验证通过 / Validation Passed")
    else:
        print("[X] 验证失败 / Validation Failed")
        print("\n建议 / Suggestions:")
        print("  1. 确保 MiniQMT 客户端正在运行 / Ensure MiniQMT client is running")
        print("  2. 运行设置向导: python setup_live_trading.py / Run setup wizard")
        print("  3. 检查配置文件 ~/QMT_Strategy_Data/strategy_config.json")
        print("     Check config file ~/QMT_Strategy_Data/strategy_config.json")

    return all_ok


def main():
    """
    主函数
    """
    global engine

    # 解析命令行参数
    args = parse_args()

    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 80)
    print("全天候策略实盘执行系统")
    print("=" * 80)

    # 1. 加载配置
    print("\n1. 加载配置...")
    config = ConfigLoader.load_strategy_config()

    # 从命令行参数覆盖配置
    if args.account_id:
        config['xtquant_account_id'] = args.account_id
    if args.session_id:
        config['xtquant_session_id'] = args.session_id

    # 验证必需配置
    required_configs = ['xtquant_account_id', 'xtquant_session_id']
    missing_configs = [cfg for cfg in required_configs if not config.get(cfg)]
    if missing_configs and args.mode == 'live' and not args.dry_run:
        print(f"\n错误: 缺少必需的配置项: {missing_configs}")
        print("请在配置文件中设置或通过命令行参数指定")
        return 1

    print(f"   账户ID: {config.get('xtquant_account_id', 'N/A')}")
    print(f"   会话ID: {config.get('xtquant_session_id', 'N/A')}")
    print(f"   仓位比例: {config.get('all_weather_position_ratio', 0.5) * 100:.1f}%")
    print(f"   再平衡周期: {config.get('rebalance_period', 60)}天")

    # Extract xtquant_path with fallback
    xtquant_path = config.get('xtquant_path', '')
    if not xtquant_path:
        print("   警告: xtquant_path未配置，使用系统默认")
        print("   Warning: xtquant_path not configured, using system default")
    else:
        print(f"   QMT路径: {xtquant_path}")

    # Extract timeout configurations with defaults
    api_timeout = config.get('api_timeout', 5.0)
    max_retries = config.get('max_retries', 3)
    callback_timeout = config.get('callback_timeout', 2.0)

    print(f"   API超时时间: {api_timeout}秒")
    print(f"   最大重试次数: {max_retries}")
    print(f"   回调超时时间: {callback_timeout}秒")

    # 1.5 验证设置（仅对live模式）
    if args.mode == 'live':
        if not validate_live_trading_setup(config, args.mode, args.dry_run):
            if not args.dry_run:
                # Live mode failed validation
                print("\n实盘模式验证失败，退出程序 / Live mode validation failed, exiting")
                return 1
            else:
                # Dry-run mode, continue even with validation warnings
                print("\n注意：模拟模式将继续运行 / Note: Dry-run mode will continue")

    # 2. 初始化策略
    print("\n2. 初始化策略...")
    strategy = AllWeatherStrategy(config)

    etf_universe = strategy.get_etf_universe()
    print(f"   策略类型: 全天候资产配置")
    print(f"   ETF数量: {len(etf_universe)}")
    print(f"   ETF列表: {', '.join(etf_universe[:5])}...")

    # 3. 初始化交易接口
    print("\n3. 初始化交易接口...")
    trader = XtTrader(
        account_id=config['xtquant_account_id'],
        session_id=config['xtquant_session_id'],
        xtquant_path=xtquant_path,
        api_timeout=api_timeout,
        max_retries=max_retries
    )

    if args.dry_run or args.mode == 'test':
        print("   [WARNING] Test mode: No actual orders will be placed")
    else:
        print(f"   连接账户: {config['xtquant_account_id']}")

    # 4. 初始化数据接口
    print("\n4. 初始化数据接口...")
    use_cache = not args.no_cache
    data_feed = XtDataFeed(use_cache=use_cache)
    print(f"   缓存: {'启用' if use_cache else '禁用'}")

    # 5. 创建实盘引擎
    print("\n5. 创建实盘引擎...")
    config['strategy_name'] = args.strategy
    engine = LiveTradingEngine(
        strategy=strategy,
        trader=trader,
        data_feed=data_feed,
        config=config
    )

    # 6. 初始化引擎
    print("\n6. 初始化引擎...")

    if args.dry_run or args.mode == 'test':
        print("   [WARNING] Test mode: Skipping actual connection")
        print("   [OK] Engine initialized (test mode)")
        # 在测试模式下，手动设置初始化标志
        engine.is_initialized = True
    else:
        if not engine.initialize():
            print("\n[X] Engine initialization failed")
            return 1
        print("   [OK] Engine initialized")

    # 7. 运行策略
    print("\n" + "=" * 80)
    print("策略开始运行")
    print("=" * 80)

    try:
        if args.once:
            # 只执行一次
            print("执行模式: 单次执行\n")
            success = engine.run_once()
            if success:
                print("\n[OK] Strategy execution succeeded")
                return 0
            else:
                print("\n[X] Strategy execution failed")
                return 1
        else:
            # 持续运行
            print(f"执行模式: 循环执行（间隔 {args.interval}秒）\n")
            engine.run_loop(interval=args.interval)
            return 0

    except Exception as e:
        print(f"\n[X] Strategy runtime error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # 清理资源
        print("\n清理资源...")
        if engine:
            engine.stop()


if __name__ == '__main__':
    sys.exit(main())
