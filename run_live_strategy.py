# encoding:gbk
"""
全天候策略实盘执行脚本
程序入口，负责初始化并运行实盘策略
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
        xtquant_path=config.get('xtquant_path', None)
    )

    if args.dry_run or args.mode == 'test':
        print("   ⚠ 测试模式: 不会实际下单")
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
        print("   ⚠ 测试模式: 跳过实际连接")
        print("   ✓ 引擎初始化完成（模拟模式）")
        return 0
    else:
        if not engine.initialize():
            print("\n✗ 引擎初始化失败")
            return 1
        print("   ✓ 引擎初始化完成")

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
                print("\n✓ 策略执行成功")
                return 0
            else:
                print("\n✗ 策略执行失败")
                return 1
        else:
            # 持续运行
            print(f"执行模式: 循环执行（间隔 {args.interval}秒）\n")
            engine.run_loop(interval=args.interval)
            return 0

    except Exception as e:
        print(f"\n✗ 策略运行异常: {e}")
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
