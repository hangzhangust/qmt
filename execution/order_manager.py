# -*- coding: utf-8 -*-
"""
Order Manager Module
Order lifecycle management and order placement logic
"""
import time
from typing import Dict, List, Optional
from .xt_trader import XtTrader


class OrderManager:
    """
    订单管理器
    负责订单的下单、查询、撤单等操作
    """

    def __init__(self, trader: XtTrader):
        """
        初始化订单管理器

        参数:
            trader: XtTrader交易接口实例
        """
        self.trader = trader
        self.pending_orders = {}  # 待处理订单 {order_id: order_info}

        print("[OrderManager] 订单管理器初始化完成")

    def place_order(self, stock_code: str, order_type: str,
                    volume: int, price_type: str = 'limit',
                    price: float = None, strategy_name: str = 'all_weather',
                    remark: str = '', wait_filled: bool = True,
                    timeout: int = 30) -> Optional[Dict]:
        """
        下单（高级封装）

        参数:
            stock_code: 股票代码（如 "000001.SZ"）
            order_type: 订单类型 ('buy' 或 'sell')
            volume: 目标金额（元）或数量（股）
            price_type: 价格类型 ('limit'=限价单, 'market'=市价单)
            price: 价格（限价单必须，市价单传None）
            strategy_name: 策略名称
            remark: 备注
            wait_filled: 是否等待订单成交
            timeout: 等待超时时间（秒）

        返回:
            dict: 订单信息
                - success: 是否成功
                - order_id: 订单ID
                - stock_code: 股票代码
                - order_type: 订单类型
                - volume: 数量
                - price: 价格
                - status: 订单状态
        """
        try:
            # 参数验证
            if order_type not in ['buy', 'sell']:
                return {'success': False, 'error_msg': f'无效的订单类型: {order_type}'}

            # 买入时检查可用资金
            if order_type == 'buy':
                account_info = self.trader.query_account()
                if account_info:
                    required_cash = volume * price if price else volume * 100  # 估算
                    if account_info['cash'] < required_cash:
                        return {
                            'success': False,
                            'error_msg': f'资金不足: 需要{required_cash:.2f}, 可用{account_info["cash"]:.2f}'
                        }

            # 卖出时检查持仓
            if order_type == 'sell':
                position = self.trader.query_position(stock_code)
                if not position or position['can_use_volume'] < volume:
                    available = position['can_use_volume'] if position else 0
                    return {
                        'success': False,
                        'error_msg': f'持仓不足: 需要{volume}股, 可用{available}股'
                    }

            # 下单
            result = self.trader.order_stock(
                stock_code=stock_code,
                order_type=order_type,
                volume=volume,
                price_type=price_type,
                price=price,
                strategy_name=strategy_name,
                remark=remark
            )

            if not result['success']:
                return result

            order_id = result['order_id']

            # 保存到待处理订单列表
            self.pending_orders[order_id] = {
                'order_id': order_id,
                'stock_code': stock_code,
                'order_type': order_type,
                'volume': volume,
                'price': price,
                'timestamp': time.time()
            }

            # 等待订单成交
            if wait_filled:
                status = self.wait_order_filled(order_id, timeout)
                result['status'] = status
            else:
                result['status'] = 'submitted'

            return result

        except Exception as e:
            error_msg = f"下单异常: {e}"
            print(f"[OrderManager] {error_msg}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error_msg': error_msg}

    def cancel_order(self, order_id: str) -> bool:
        """
        撤单

        参数:
            order_id: 订单ID

        返回:
            bool: 是否成功
        """
        try:
            # 调用交易接口撤单
            success = self.trader.cancel_order(order_id)

            if success:
                # 从待处理订单中移除
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]
                print(f"[OrderManager] 撤单成功: {order_id}")
            else:
                print(f"[OrderManager] 撤单失败: {order_id}")

            return success

        except Exception as e:
            print(f"[OrderManager] 撤单异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_order_status(self, order_id: str) -> Optional[str]:
        """
        获取订单状态

        参数:
            order_id: 订单ID

        返回:
            str: 订单状态
                - 'submitted': 已报
                - 'filled': 已成
                - 'partial_filled': 部成
                - 'cancelled': 已撤
                - 'rejected': 已被拒绝
                - 'unknown': 未知
        """
        try:
            # 查询委托列表
            orders = self.trader.query_orders()

            # 查找指定订单
            for order in orders:
                if order['order_id'] == order_id:
                    # 映射状态码
                    order_status = order['order_status']
                    traded_volume = order['traded_volume']
                    order_volume = order['order_volume']

                    if traded_volume == 0:
                        return 'submitted'
                    elif traded_volume < order_volume:
                        return 'partial_filled'
                    elif traded_volume == order_volume:
                        return 'filled'
                    else:
                        return 'unknown'

            # 未找到订单
            return 'unknown'

        except Exception as e:
            print(f"[OrderManager] 查询订单状态异常: {e}")
            return 'unknown'

    def get_pending_orders(self) -> List[Dict]:
        """
        获取未完成订单

        返回:
            list: 未完成订单列表
        """
        try:
            # 查询所有委托
            orders = self.trader.query_orders()

            # 筛选未完成的订单
            pending = []
            for order in orders:
                traded_volume = order['traded_volume']
                order_volume = order['order_volume']

                # 未成交或部分成交
                if traded_volume < order_volume:
                    pending.append(order)

            return pending

        except Exception as e:
            print(f"[OrderManager] 查询未完成订单异常: {e}")
            return []

    def wait_order_filled(self, order_id: str, timeout: int = 30) -> str:
        """
        等待订单成交

        参数:
            order_id: 订单ID
            timeout: 超时时间（秒）

        返回:
            str: 订单状态
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 查询订单状态
            status = self.get_order_status(order_id)

            if status == 'filled':
                print(f"[OrderManager] 订单已成交: {order_id}")
                # 从待处理订单中移除
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]
                return 'filled'

            elif status in ['cancelled', 'rejected']:
                print(f"[OrderManager] 订单已取消/拒绝: {order_id}")
                # 从待处理订单中移除
                if order_id in self.pending_orders:
                    del self.pending_orders[order_id]
                return status

            # 等待一段时间再查询
            time.sleep(1)

        # 超时
        print(f"[OrderManager] 等待订单成交超时: {order_id}")
        return 'timeout'

    def cancel_all_pending_orders(self) -> int:
        """
        撤销所有未完成订单

        返回:
            int: 成功撤销的订单数量
        """
        pending_orders = self.get_pending_orders()
        cancelled_count = 0

        for order in pending_orders:
            order_id = order['order_id']
            if self.cancel_order(order_id):
                cancelled_count += 1

        print(f"[OrderManager] 撤销了 {cancelled_count}/{len(pending_orders)} 个订单")
        return cancelled_count

    def calculate_target_volume(self, target_value: float, current_price: float) -> int:
        """
        计算目标持仓量（按手，100股一手）

        参数:
            target_value: 目标金额（元）
            current_price: 当前价格（元）

        返回:
            int: 目标持仓量（股）
        """
        if current_price <= 0:
            return 0

        # 计算目标股数（向下取整到100的倍数）
        target_volume = int(target_value / current_price / 100) * 100

        return target_volume

    def calculate_rebalance_orders(self, current_holdings: Dict[str, Dict],
                                   target_allocations: Dict[str, float],
                                   current_prices: Dict[str, float]) -> List[Dict]:
        """
        计算再平衡订单列表

        参数:
            current_holdings: 当前持仓 {stock_code: {volume, market_value, ...}}
            target_allocations: 目标配置 {stock_code: target_value}
            current_prices: 当前价格 {stock_code: price}

        返回:
            list: 订单列表
                [
                    {
                        'stock_code': '000001.SZ',
                        'action': 'buy' or 'sell',
                        'volume': 100,
                        'target_value': 10000.0,
                        'current_value': 8000.0,
                        'price': 5.5
                    },
                    ...
                ]
        """
        orders = []

        # FIX: Filter current_holdings to only include stocks in target_allocations
        # Stocks not in target list are ignored (not considered in rebalancing)
        filtered_holdings = {
            stock_code: holding
            for stock_code, holding in current_holdings.items()
            if stock_code in target_allocations
        }

        for stock_code, target_value in target_allocations.items():
            # 获取当前价格
            current_price = current_prices.get(stock_code, 0)
            if current_price <= 0:
                print(f"[OrderManager] 警告: {stock_code} 价格无效，跳过")
                continue

            # 计算目标持仓量
            target_volume = self.calculate_target_volume(target_value, current_price)

            # 获取当前持仓 (from filtered holdings)
            if stock_code in filtered_holdings:
                current_volume = filtered_holdings[stock_code].get('volume', 0)
            else:
                current_volume = 0

            # 计算差异
            volume_diff = target_volume - current_volume

            # 如果差异不为0，生成订单
            if volume_diff > 0:
                # 买入
                orders.append({
                    'stock_code': stock_code,
                    'action': 'buy',
                    'volume': volume_diff,
                    'target_value': target_value,
                    'current_value': current_volume * current_price,
                    'price': current_price
                })
            elif volume_diff < 0:
                # 卖出
                orders.append({
                    'stock_code': stock_code,
                    'action': 'sell',
                    'volume': abs(volume_diff),
                    'target_value': target_value,
                    'current_value': current_volume * current_price,
                    'price': current_price
                })

        return orders


# 测试代码
if __name__ == '__main__':
    # 测试订单管理器
    print("=" * 60)
    print("订单管理器测试")
    print("=" * 60)

    # 创建交易接口（需要实际的账户ID）
    from .xt_trader import XtTrader

    test_account_id = "your_account_id"
    trader = XtTrader(account_id=test_account_id, session_id=123456)

    if trader.connect():
        print("✓ 连接成功")

        # 创建订单管理器
        order_mgr = OrderManager(trader)

        # 测试计算目标持仓量
        print("\n--- 测试计算目标持仓量 ---")
        target_volume = order_mgr.calculate_target_volume(10000, 5.5)
        print(f"目标金额: 10000元, 价格: 5.5元 -> 目标持仓: {target_volume}股")

        # 测试计算再平衡订单
        print("\n--- 测试计算再平衡订单 ---")
        current_holdings = {
            '000001.SZ': {'volume': 1000, 'market_value': 5500},
            '510300.SH': {'volume': 500, 'market_value': 2000}
        }
        target_allocations = {
            '000001.SZ': 6000,
            '510300.SH': 3000
        }
        current_prices = {
            '000001.SZ': 5.5,
            '510300.SH': 4.0
        }

        orders = order_mgr.calculate_rebalance_orders(
            current_holdings, target_allocations, current_prices
        )

        print(f"生成的订单数量: {len(orders)}")
        for order in orders:
            print(f"  {order['stock_code']}: {order['action']} {order['volume']}股")

        # 断开连接
        trader.disconnect()
    else:
        print("✗ 连接失败")
