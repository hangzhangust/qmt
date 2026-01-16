# -*- coding: utf-8 -*-
"""
Live Trading Engine Module
Integrates strategy logic, trading interface, and data interface
"""
import datetime
import time
from typing import Dict, Optional
from strategies.base_strategy import BaseStrategy
from .xt_trader import XtTrader
from .order_manager import OrderManager
from data.xtdata_feed import XtDataFeed
from utils.state_manager import StateManager


class LiveTradingEngine:
    """
    实盘交易引擎
    负责策略的主循环、持仓管理、再平衡执行
    """

    def __init__(self, strategy: BaseStrategy, trader: XtTrader,
                 data_feed: XtDataFeed, config: Dict):
        """
        初始化实盘交易引擎

        参数:
            strategy: 策略实例
            trader: 交易接口实例
            data_feed: 数据接口实例
            config: 配置字典
        """
        self.strategy = strategy
        self.trader = trader
        self.data_feed = data_feed
        self.config = config

        # 创建订单管理器
        self.order_manager = OrderManager(trader)

        # 创建状态管理器
        state_dir = config.get('state_dir', None)
        self.state_manager = StateManager(state_dir=state_dir)

        # 策略状态
        self.is_running = False
        self.is_initialized = False

        # 获取策略名称
        self.strategy_name = config.get('strategy_name', 'unknown')

        print(f"[LiveEngine] 实盘交易引擎初始化完成: {self.strategy_name}")

    def initialize(self) -> bool:
        """
        初始化引擎
        - 恢复策略状态
        - 加载历史数据
        - 检查账户连接

        返回:
            bool: 是否初始化成功
        """
        try:
            print("=" * 60)
            print("实盘交易引擎初始化")
            print("=" * 60)

            # 1. 检查交易连接
            if not self.trader.connected:
                print("[LiveEngine] 交易接口未连接，尝试连接...")
                if not self.trader.connect():
                    print("[LiveEngine] 错误: 交易接口连接失败")
                    return False
            print("✓ 交易接口已连接")

            # 2. 恢复策略状态
            print("\n--- 恢复策略状态 ---")
            state = self.state_manager.load_state(self.strategy_name)
            if state:
                self.strategy.restore_state(state)
                print(f"✓ 策略状态已恢复: {state}")
            else:
                print("✗ 未找到历史状态，使用初始状态")

            # 3. 查询账户信息
            print("\n--- 账户信息 ---")
            account_info = self.trader.query_account()
            if not account_info:
                print("[LiveEngine] 错误: 无法查询账户信息")
                return False

            print(f"总资产: {account_info['total_asset']:.2f}")
            print(f"可用资金: {account_info['cash']:.2f}")
            print(f"证券市值: {account_info['market_value']:.2f}")

            # 4. 查询当前持仓
            print("\n--- 当前持仓 ---")
            positions = self.trader.query_positions()
            if positions:
                for pos in positions:
                    print(f"{pos['stock_code']}: {pos['volume']}股, "
                          f"市值{pos['market_value']:.2f}")
            else:
                print("无持仓")

            self.is_initialized = True
            print("\n✓ 引擎初始化完成")
            return True

        except Exception as e:
            print(f"[LiveEngine] 初始化异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_once(self) -> bool:
        """
        执行一次策略逻辑
        - 检查交易时间
        - 查询账户和持仓
        - 计算目标配置
        - 执行再平衡
        - 保存状态

        返回:
            bool: 是否执行成功
        """
        try:
            # 1. 检查是否初始化
            if not self.is_initialized:
                print("[LiveEngine] 引擎未初始化")
                return False

            # 2. 检查交易时间
            if not self.check_trading_time():
                return False

            print("\n" + "=" * 60)
            print(f"策略执行: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

            # 3. 查询账户信息
            account_info = self.trader.query_account()
            if not account_info:
                print("[LiveEngine] 无法查询账户信息")
                return False

            total_assets = account_info['total_asset']
            print(f"总资产: {total_assets:.2f}")

            # 4. 查询当前持仓
            current_holdings = self.get_current_holdings()
            print(f"当前持仓数量: {len(current_holdings)}")

            # 5. 检查是否需要再平衡
            current_date = datetime.datetime.now().strftime('%Y%m%d')
            need_rebalance = self.strategy.check_rebalance_condition(current_date)

            if not need_rebalance:
                print("未达到再平衡条件，跳过本次执行")
                return True

            # 6. 计算目标配置
            print("\n--- 计算目标配置 ---")
            target_allocations = self.strategy.calculate_targets(total_assets)
            print(f"目标配置数量: {len(target_allocations)}")

            for stock_code, target_value in target_allocations.items():
                print(f"  {stock_code}: {target_value:.2f}元")

            # 7. 获取当前价格
            print("\n--- 获取当前价格 ---")
            current_prices = self.get_current_prices(list(target_allocations.keys()))
            print(f"获取到 {len(current_prices)} 个价格")

            # 8. 执行再平衡
            print("\n--- 执行再平衡 ---")
            success = self.execute_rebalance(target_allocations, current_prices, current_holdings)

            if success:
                print("✓ 再平衡执行成功")

                # 更新策略的再平衡时间
                self.strategy.update_rebalance_time(current_date)

                # 9. 保存状态
                self.save_state()
            else:
                print("✗ 再平衡执行失败")

            return success

        except Exception as e:
            print(f"[LiveEngine] 执行异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_loop(self, interval: int = 60) -> None:
        """
        持续运行策略主循环

        参数:
            interval: 执行间隔（秒）
        """
        self.is_running = True

        print(f"\n[LiveEngine] 策略开始运行，执行间隔: {interval}秒")
        print("[LiveEngine] 按Ctrl+C停止\n")

        try:
            while self.is_running:
                # 执行一次策略
                self.run_once()

                # 等待下一次执行
                print(f"\n等待 {interval} 秒后执行下一次检查...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n[LiveEngine] 收到停止信号，正在退出...")
            self.is_running = False

        finally:
            # 保存最终状态
            self.save_state()
            print("[LiveEngine] 策略已停止")

    def check_trading_time(self) -> bool:
        """
        检查是否在交易时间

        返回:
            bool: 是否在交易时间
        """
        now = datetime.datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()

        # 周末不交易（周一=0, 周日=6）
        if current_weekday >= 5:
            return False

        # 交易时间：09:30-11:30, 13:00-15:00
        morning_start = datetime.time(9, 30)
        morning_end = datetime.time(11, 30)
        afternoon_start = datetime.time(13, 0)
        afternoon_end = datetime.time(15, 0)

        is_trading = (morning_start <= current_time <= morning_end or
                      afternoon_start <= current_time <= afternoon_end)

        if not is_trading:
            print(f"[LiveEngine] 当前不在交易时间: {current_time}")

        return is_trading

    def get_current_holdings(self) -> Dict[str, Dict]:
        """
        获取当前持仓

        返回:
            dict: 当前持仓 {stock_code: {volume, market_value, ...}}
        """
        positions = self.trader.query_positions()

        holdings = {}
        for pos in positions:
            holdings[pos['stock_code']] = {
                'volume': pos['volume'],
                'can_use_volume': pos['can_use_volume'],
                'market_value': pos['market_value'],
                'cost_price': pos['open_price'],
                'pnl_ratio': pos['pnl_ratio'],
                'pnl_money': pos['pnl_money']
            }

        return holdings

    def get_current_prices(self, stock_codes: list) -> Dict[str, float]:
        """
        获取当前价格

        参数:
            stock_codes: 股票代码列表

        返回:
            dict: 当前价格 {stock_code: price}
        """
        prices = {}

        try:
            # 使用miniQMT数据接口获取最新价格
            tick_data = self.data_feed.get_market_data(
                field_list=['close'],
                stock_list=stock_codes,
                period='1d',
                count=1,
                dividend_type='follow'
            )

            for stock_code in stock_codes:
                if stock_code in tick_data:
                    df = tick_data[stock_code]
                    if not df.empty:
                        prices[stock_code] = df['close'].iloc[-1]
                    else:
                        prices[stock_code] = 0
                else:
                    prices[stock_code] = 0

        except Exception as e:
            print(f"[LiveEngine] 获取价格失败: {e}")

        return prices

    def execute_rebalance(self, target_allocations: Dict[str, float],
                          current_prices: Dict[str, float],
                          current_holdings: Dict[str, Dict]) -> bool:
        """
        执行再平衡

        参数:
            target_allocations: 目标配置 {stock_code: target_value}
            current_prices: 当前价格 {stock_code: price}
            current_holdings: 当前持仓

        返回:
            bool: 是否成功
        """
        try:
            # 计算再平衡订单
            orders = self.order_manager.calculate_rebalance_orders(
                current_holdings, target_allocations, current_prices
            )

            if not orders:
                print("无需调整，持仓已符合目标配置")
                return True

            print(f"需要执行 {len(orders)} 笔交易\n")

            # 显示调整计划
            print(f"{'股票代码':<15} {'操作':<6} {'数量':>10} {'价格':>10} {'金额':>15}")
            print("-" * 60)

            for order in orders:
                stock_code = order['stock_code']
                action = order['action']
                volume = order['volume']
                price = order['price']
                amount = volume * price

                action_str = '买入' if action == 'buy' else '卖出'
                print(f"{stock_code:<15} {action_str:<6} {volume:>10} {price:>10.2f} {amount:>15.2f}")

            print("-" * 60)

            # 执行订单（先卖出后买入，确保有足够资金）
            sell_orders = [o for o in orders if o['action'] == 'sell']
            buy_orders = [o for o in orders if o['action'] == 'buy']

            # 1. 先执行卖出订单
            if sell_orders:
                print("\n执行卖出订单...")
                for order in sell_orders:
                    self._execute_single_order(order, 'market')

            # 2. 再执行买入订单
            if buy_orders:
                print("\n执行买入订单...")

                # 查询可用资金
                account_info = self.trader.query_account()
                available_cash = account_info['cash'] if account_info else 0

                # 按金额排序，优先买入金额小的
                buy_orders_sorted = sorted(buy_orders, key=lambda x: x['volume'] * x['price'])

                for order in buy_orders_sorted:
                    # 检查资金
                    required_cash = order['volume'] * order['price']
                    if available_cash < required_cash:
                        print(f"资金不足，跳过 {order['stock_code']}: "
                              f"需要{required_cash:.2f}, 可用{available_cash:.2f}")
                        continue

                    # 执行买入
                    result = self._execute_single_order(order, 'market')
                    if result and result.get('success'):
                        available_cash -= required_cash

            return True

        except Exception as e:
            print(f"[LiveEngine] 再平衡异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _execute_single_order(self, order: Dict, price_type: str = 'market') -> Optional[Dict]:
        """
        执行单个订单

        参数:
            order: 订单信息
            price_type: 价格类型

        返回:
            dict: 订单结果
        """
        stock_code = order['stock_code']
        action = order['action']
        volume = order['volume']
        price = order.get('price', None)

        # 使用订单管理器下单
        result = self.order_manager.place_order(
            stock_code=stock_code,
            order_type=action,
            volume=volume,
            price_type=price_type,
            price=price,
            strategy_name=self.strategy_name,
            remark=f"再平衡_{self.strategy_name}",
            wait_filled=True,
            timeout=30
        )

        return result

    def save_state(self) -> None:
        """保存策略状态"""
        try:
            state = self.strategy.get_state()
            self.state_manager.save_state(self.strategy_name, state)
            print(f"[LiveEngine] 策略状态已保存: {self.strategy_name}")
        except Exception as e:
            print(f"[LiveEngine] 保存状态失败: {e}")

    def stop(self) -> None:
        """停止引擎"""
        print("[LiveEngine] 正在停止引擎...")
        self.is_running = False

        # 保存状态
        self.save_state()

        # 断开交易连接
        if self.trader:
            self.trader.disconnect()

        print("[LiveEngine] 引擎已停止")


# 测试代码
if __name__ == '__main__':
    # 测试实盘交易引擎
    print("=" * 60)
    print("实盘交易引擎测试")
    print("=" * 60)

    # 注意：这需要实际的交易账户
    from strategies.all_weather_strategy import AllWeatherStrategy
    from utils.config_loader import ConfigLoader

    # 加载配置
    config = ConfigLoader.load_strategy_config()

    # 创建策略
    strategy = AllWeatherStrategy(config)

    # 创建交易接口（需要实际账户ID）
    account_id = config.get('xtquant_account_id', 'your_account_id')
    trader = XtTrader(account_id=account_id, session_id=config.get('xtquant_session_id', 0))

    # 创建数据接口
    data_feed = XtDataFeed(use_cache=True)

    # 创建引擎
    engine = LiveTradingEngine(
        strategy=strategy,
        trader=trader,
        data_feed=data_feed,
        config=config
    )

    # 初始化引擎
    if engine.initialize():
        print("\n✓ 引擎初始化成功")

        # 执行一次
        print("\n--- 执行一次策略 ---")
        engine.run_once()

        # 停止引擎
        engine.stop()
    else:
        print("\n✗ 引擎初始化失败")
