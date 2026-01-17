# -*- coding: utf-8 -*-
"""
Live Trading Setup Script
实盘交易设置脚本
Guides user through configuring and testing live trading setup
"""
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """Print welcome banner"""
    print("=" * 80)
    print("全天候策略实盘交易设置向导")
    print("All-Weather Strategy Live Trading Setup Wizard")
    print("=" * 80)
    print()


def check_miniqmt():
    """Check if MiniQMT is running"""
    print("\n1. 检查 MiniQMT 连接 / Checking MiniQMT Connection")
    print("-" * 80)

    try:
        from xtquant import xtdata

        # Try to get some data to verify connection
        result = xtdata.get_full_tick(['000001.SZ'])

        if result is not None:
            print("[OK] MiniQMT 连接正常 / MiniQMT Connected")
            return True
        else:
            print("[X] MiniQMT 未响应 / MiniQMT Not Responding")
            print("请确保 MiniQMT 客户端正在运行 / Please ensure MiniQMT client is running")
            return False

    except ImportError:
        print("[X] xtquant 模块未安装 / xtquant module not installed")
        print("请运行: pip install xtquant / Please run: pip install xtquant")
        return False
    except Exception as e:
        print(f"[X] 连接失败 / Connection failed: {e}")
        return False


def get_account_config():
    """Get account configuration from user"""
    print("\n2. 配置交易账户 / Configure Trading Account")
    print("-" * 80)

    account_id = ""
    while not account_id:
        print("\n请输入您的账户ID / Please enter your account ID:")
        print("格式示例 / Format example: 123456.SH (上海) 或 123456.SZ (深圳)")
        account_id = input("账户ID / Account ID: ").strip()

        if not account_id:
            print("账户ID不能为空 / Account ID cannot be empty")
            continue

        # Validate format
        if '.' not in account_id:
            print("警告: 账户ID应包含市场后缀 (.SH 或 .SZ) / Warning: Account ID should include market suffix (.SH or .SZ)")
            add_suffix = input("是否添加后缀? / Add suffix? (y/n): ").strip().lower()
            if add_suffix == 'y':
                market = input("请输入市场 / Enter market (SH/SZ): ").strip().upper()
                if market in ['SH', 'SZ']:
                    account_id = f"{account_id}.{market}"
                else:
                    print("无效的市场代码，请重新输入 / Invalid market code")
                    account_id = ""
                    continue
        else:
            # Validate market suffix
            market = account_id.split('.')[-1]
            if market not in ['SH', 'SZ']:
                print(f"无效的市场后缀: {market}，应为 SH 或 SZ / Invalid market suffix: {market}, should be SH or SZ")
                account_id = ""
                continue

        print(f"账户ID / Account ID: {account_id}")
        confirm = input("确认无误? / Confirm? (y/n): ").strip().lower()
        if confirm != 'y':
            account_id = ""

    session_id = ""
    while session_id == "":
        print("\n请输入会话ID / Please enter session ID:")
        print("默认值 / Default: 123456")
        session_input = input("会话ID / Session ID (留空使用默认值/press Enter for default): ").strip()

        if not session_input:
            session_id = "123456"
        else:
            try:
                # Validate it's a number
                int(session_input)
                session_id = session_input
            except ValueError:
                print("会话ID必须是数字 / Session ID must be a number")
                session_id = ""

        print(f"会话ID / Session ID: {session_id}")

    return account_id, int(session_id)


def test_trader_connection(account_id, session_id):
    """Test trader connection"""
    print("\n3. 测试交易接口连接 / Testing Trading Interface Connection")
    print("-" * 80)

    try:
        from execution.xt_trader import XtTrader

        trader = XtTrader(account_id=account_id, session_id=session_id)

        if trader.connect():
            print("[OK] 交易接口连接成功 / Trading Interface Connected")

            # Query account info
            account_info = trader.query_account()
            if account_info:
                print(f"\n账户信息 / Account Info:")
                print(f"  总资产 / Total Asset: {account_info['total_asset']:,.2f}")
                print(f"  可用资金 / Cash: {account_info['cash']:,.2f}")
                print(f"  证券市值 / Market Value: {account_info['market_value']:,.2f}")

            # Query positions
            positions = trader.query_positions()
            if positions:
                print(f"\n当前持仓 / Current Positions:")
                for pos in positions[:5]:  # Show first 5
                    print(f"  {pos['stock_code']}: {pos['volume']}股, 市值{pos['market_value']:,.2f}")
                if len(positions) > 5:
                    print(f"  ... 还有 {len(positions) - 5} 只股票 / ... and {len(positions) - 5} more stocks")
            else:
                print("\n当前无持仓 / No current positions")

            trader.disconnect()
            return True
        else:
            print("[X] 交易接口连接失败 / Trading Interface Connection Failed")
            return False

    except Exception as e:
        print(f"[X] 测试失败 / Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_config(account_id, session_id):
    """Save configuration to file"""
    print("\n4. 保存配置 / Saving Configuration")
    print("-" * 80)

    try:
        from utils.config_loader import ConfigLoader

        # Load existing config or create new
        config = ConfigLoader.load_strategy_config()

        # Update with new values
        config['xtquant_account_id'] = account_id
        config['xtquant_session_id'] = session_id

        # Save config
        home_dir = os.path.expanduser("~")
        config_file = os.path.join(home_dir, "QMT_Strategy_Data", "strategy_config.json")

        if ConfigLoader.save_config(config, config_file):
            print(f"[OK] 配置已保存 / Configuration saved to:")
            print(f"    {config_file}")
            return True
        else:
            print("[X] 配置保存失败 / Failed to save configuration")
            return False

    except Exception as e:
        print(f"[X] 保存配置失败 / Failed to save configuration: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_dry_run_test():
    """Run a dry-run test"""
    print("\n5. 运行模拟测试 / Running Dry-Run Test")
    print("-" * 80)

    try:
        print("准备运行策略模拟测试... / Preparing to run strategy dry-run test...")
        print("这将测试策略逻辑但不会实际下单 / This will test strategy logic without placing actual orders")

        run_test = input("\n是否运行模拟测试? / Run dry-run test? (y/n): ").strip().lower()
        if run_test != 'y':
            print("跳过模拟测试 / Skipping dry-run test")
            return True

        print("\n正在运行模拟测试... / Running dry-run test...")
        print("注意：这可能需要几分钟时间 / Note: This may take several minutes")

        # Import and run
        from strategies.all_weather_strategy import AllWeatherStrategy
        from utils.config_loader import ConfigLoader

        # Load config
        config = ConfigLoader.load_strategy_config()

        # Create strategy
        strategy = AllWeatherStrategy(config)

        # Get ETF universe
        etf_universe = strategy.get_etf_universe()
        print(f"\n策略配置 / Strategy Configuration:")
        print(f"  ETF数量 / ETF Count: {len(etf_universe)}")
        print(f"  仓位比例 / Position Ratio: {config['all_weather_position_ratio']*100:.1f}%")
        print(f"  再平衡周期 / Rebalance Period: {config['rebalance_period']}天")

        # Calculate targets (with 1M RMB)
        print(f"\n计算目标配置（假设总资产100万）/ Calculating target allocation (assuming 1M total assets):")
        targets = strategy.calculate_targets(1000000)

        print(f"\n目标配置 / Target Allocation:")
        for stock_code, target_value in sorted(targets.items()):
            print(f"  {stock_code}: {target_value:,.2f}元")

        print("\n[OK] 策略计算成功 / Strategy calculation successful")
        return True

    except Exception as e:
        print(f"\n[X] 模拟测试失败 / Dry-run test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(success_dict):
    """Print setup summary"""
    print("\n" + "=" * 80)
    print("设置总结 / Setup Summary")
    print("=" * 80)

    print(f"\n1. MiniQMT连接 / MiniQMT Connection: ", end="")
    print("[OK]" if success_dict.get('miniqmt') else "[X] FAILED")

    print(f"2. 账户配置 / Account Configuration: ", end="")
    print("[OK]" if success_dict.get('config') else "[X] FAILED")

    print(f"3. 交易接口测试 / Trading Interface Test: ", end="")
    print("[OK]" if success_dict.get('trader_test') else "[X] FAILED")

    print(f"4. 配置保存 / Configuration Saved: ", end="")
    print("[OK]" if success_dict.get('save_config') else "[X] FAILED")

    print(f"5. 模拟测试 / Dry-Run Test: ", end="")
    print("[OK]" if success_dict.get('dry_run') else "[X] SKIPPED/FAILED")

    all_success = all(success_dict.values())

    if all_success:
        print("\n" + "=" * 80)
        print("[OK] 所有设置完成！/ All Setup Complete!")
        print("=" * 80)
        print("\n您现在可以运行实盘交易：/ You can now run live trading:")
        print("  python run_live_strategy.py --mode live --dry_run  # 模拟模式 / Dry-run mode")
        print("  python run_live_strategy.py --mode live            # 实盘模式 / Live mode")
        print("\n建议首先使用 --dry_run 参数测试：/ Recommend testing with --dry_run first:")
        print("  python run_live_strategy.py --mode live --dry_run --once")
    else:
        print("\n" + "=" * 80)
        print("[X] 设置未完成，请检查上述错误 / Setup incomplete, please check errors above")
        print("=" * 80)

    print()


def main():
    """Main function"""
    print_banner()

    success_dict = {}

    # Step 1: Check MiniQMT
    miniqmt_ok = check_miniqmt()
    success_dict['miniqmt'] = miniqmt_ok

    if not miniqmt_ok:
        print("\n请先解决MiniQMT连接问题后再继续 / Please fix MiniQMT connection before continuing")
        print_summary(success_dict)
        return 1

    # Step 2: Get account configuration
    account_id, session_id = get_account_config()
    success_dict['config'] = True

    # Step 3: Test trader connection
    trader_ok = test_trader_connection(account_id, session_id)
    success_dict['trader_test'] = trader_ok

    if not trader_ok:
        print("\n交易接口测试失败，但仍可以保存配置 / Trader test failed, but can still save config")
        save_anyway = input("是否保存配置? / Save configuration anyway? (y/n): ").strip().lower()
        if save_anyway != 'y':
            print_summary(success_dict)
            return 1

    # Step 4: Save configuration
    save_ok = save_config(account_id, session_id)
    success_dict['save_config'] = save_ok

    if not save_ok:
        print("\n配置保存失败 / Configuration save failed")
        print_summary(success_dict)
        return 1

    # Step 5: Run dry-run test
    dry_run_ok = run_dry_run_test()
    success_dict['dry_run'] = dry_run_ok

    # Print summary
    print_summary(success_dict)

    return 0 if all(success_dict.values()) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断 / User interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误 / Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
