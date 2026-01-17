# -*- coding: utf-8 -*-
"""
miniQMT Trading Interface Wrapper Module
Encapsulates xtquant.xttrader API to provide unified trading interface
"""
import time
from typing import Dict, List, Optional, Tuple
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant


class XtTraderCallback(XtQuantTraderCallback):
    """
    miniQMT交易回调类
    处理异步响应和事件通知
    """

    def __init__(self):
        """初始化回调"""
        super().__init__()
        self.order_responses = {}  # 存储异步下单响应
        self.asset_info = None  # 存储资产信息
        self.order_info = None  # 存储委托信息

    def on_order_stock_async_response(self, response):
        """
        异步下单响应回调

        参数:
            response: 下单响应对象
        """
        if response.order_id:
            print(f"[回调] 异步下单成功: {response.order_id}")
            self.order_responses[response.order_id] = {
                'success': True,
                'order_id': response.order_id
            }
        else:
            print(f"[回调] 异步下单失败: {response.error_msg}")
            self.order_responses[response.order_id] = {
                'success': False,
                'error_msg': response.error_msg
            }

    def on_stock_asset(self, asset):
        """
        资产查询回调

        参数:
            asset: 资产对象
        """
        self.asset_info = {
            'total_asset': asset.total_asset,
            'cash': asset.cash,
            'market_value': asset.market_value,
            'pnl_ratio': asset.pnl_ratio,
            'pnl_money': asset.pnl_money
        }

    def on_stock_order(self, order):
        """
        委托查询回调

        参数:
            order: 委托对象
        """
        self.order_info = {
            'order_id': order.order_id,
            'stock_code': order.stock_code,
            'order_type': order.order_type,
            'order_volume': order.order_volume,
            'price_type': order.price_type,
            'price': order.price,
            'traded_volume': order.traded_volume,
            'order_status': order.order_status,
            'strategy_name': order.strategy_name,
            'remark': order.remark
        }

    def on_stock_order_insert_err(self, error):
        """
        下单错误回调

        参数:
            error: 错误信息
        """
        print(f"[回调] 下单错误: {error}")

    def on_stock_trade(self, trade):
        """
        成交回调

        参数:
            trade: 成交对象
        """
        print(f"[回调] 成交: {trade.stock_code}, "
              f"数量: {trade.traded_volume}, "
              f"价格: {trade.traded_price}")


class XtTrader:
    """
    miniQMT交易接口封装类
    提供账户连接、资产查询、持仓查询、下单等功能
    """

    def __init__(self, account_id: str, session_id: int = 0,
                 xtquant_path: str = None, callback: XtTraderCallback = None):
        """
        初始化交易接口

        参数:
            account_id: 账户ID
            session_id: 会话ID（默认0）
            xtquant_path: miniQMT路径（默认None，使用系统默认）
            callback: 回调对象（默认None，自动创建）
        """
        self.account_id = account_id
        self.session_id = session_id
        # 确保xtquant_path不是None，默认为空字符串（使用系统默认路径）
        self.xtquant_path = xtquant_path if xtquant_path is not None else ""

        # 创建回调对象
        self.callback = callback if callback else XtTraderCallback()

        # 创建交易对象（暂不连接）
        self.trader = None
        self.account = None

        # 连接状态
        self.connected = False

        print(f"[XtTrader] 初始化交易接口: 账户ID={account_id}, 会话ID={session_id}")

    def connect(self) -> bool:
        """
        连接交易账户

        返回:
            bool: 是否连接成功
        """
        try:
            # 创建账户对象
            # account_id格式通常需要指定市场类型
            # 如果account_id包含"."，则解析市场类型，否则默认为STOCK账户
            if '.' in self.account_id:
                account_str, market_str = self.account_id.split('.')
                market = 1 if market_str == 'SH' else 0  # SH=1, SZ=0
                self.account = StockAccount(account_str, market)
            else:
                # 默认为股票账户
                self.account = StockAccount(self.account_id, "STOCK")

            # 创建交易对象
            # XtQuantTrader构造函数参数: path, session, callback=None
            self.trader = XtQuantTrader(self.xtquant_path, self.session_id, self.callback)

            # 连接账户
            connect_result = self.trader.connect()

            if connect_result == 0:
                self.connected = True
                print(f"[XtTrader] 连接成功: {self.account_id}")
                return True
            else:
                print(f"[XtTrader] 连接失败，错误码: {connect_result}")
                return False

        except Exception as e:
            print(f"[XtTrader] 连接异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect(self) -> None:
        """断开连接"""
        try:
            if self.trader and self.connected:
                self.trader.release()
                self.connected = False
                print(f"[XtTrader] 已断开连接: {self.account_id}")
        except Exception as e:
            print(f"[XtTrader] 断开连接异常: {e}")

    def query_account(self) -> Optional[Dict]:
        """
        查询账户资产信息

        返回:
            dict: 资产信息
                - total_asset: 总资产
                - cash: 可用资金
                - market_value: 证券市值
                - pnl_ratio: 盈亏比例
                - pnl_money: 盈亏金额
            如果失败返回None
        """
        try:
            if not self.connected:
                print("[XtTrader] 未连接，无法查询账户")
                return None

            # 同步查询资产
            asset = self.trader.query_stock_asset(self.account)

            if asset:
                result = {
                    'total_asset': asset.total_asset,
                    'cash': asset.cash,
                    'market_value': asset.market_value,
                    'pnl_ratio': asset.pnl_ratio,
                    'pnl_money': asset.pnl_money
                }
                print(f"[XtTrader] 账户查询成功: "
                      f"总资产={result['total_asset']:.2f}, "
                      f"可用资金={result['cash']:.2f}")
                return result
            else:
                print("[XtTrader] 账户查询失败")
                return None

        except Exception as e:
            print(f"[XtTrader] 查询账户异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    def query_positions(self) -> List[Dict]:
        """
        查询所有持仓

        返回:
            list: 持仓列表，每个持仓包含:
                - stock_code: 股票代码
                - volume: 持仓数量
                - can_use_volume: 可用数量
                - open_price: 开仓价
                - market_value: 市值
                - pnl_ratio: 盈亏比例
                - pnl_money: 盈亏金额
        """
        try:
            if not self.connected:
                print("[XtTrader] 未连接，无法查询持仓")
                return []

            # 同步查询持仓
            positions = self.trader.query_stock_positions(self.account)

            if not positions:
                print("[XtTrader] 无持仓")
                return []

            result = []
            for pos in positions:
                result.append({
                    'stock_code': pos.stock_code,
                    'volume': pos.volume,
                    'can_use_volume': pos.can_use_volume,
                    'open_price': pos.open_price,
                    'market_value': pos.market_value,
                    'pnl_ratio': pos.pnl_ratio,
                    'pnl_money': pos.pnl_money
                })

            print(f"[XtTrader] 持仓查询成功: 共{len(result)}只股票")
            return result

        except Exception as e:
            print(f"[XtTrader] 查询持仓异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def query_position(self, stock_code: str) -> Optional[Dict]:
        """
        查询单个股票持仓

        参数:
            stock_code: 股票代码（如 "000001.SZ"）

        返回:
            dict: 持仓信息，如果没有持仓返回None
        """
        positions = self.query_positions()

        for pos in positions:
            if pos['stock_code'] == stock_code:
                return pos

        return None

    def order_stock(self, stock_code: str, order_type: str,
                    volume: int, price_type: str = 'limit',
                    price: float = None, strategy_name: str = 'all_weather',
                    remark: str = '') -> Optional[Dict]:
        """
        同步下单

        参数:
            stock_code: 股票代码（如 "000001.SZ"）
            order_type: 订单类型 ('buy' 或 'sell')
            volume: 数量（股）
            price_type: 价格类型 ('limit'=限价单, 'market'=市价单)
            price: 价格（限价单必须，市价单传None）
            strategy_name: 策略名称
            remark: 备注

        返回:
            dict: 下单结果
                - success: 是否成功
                - order_id: 订单ID
                - error_msg: 错误信息
        """
        try:
            if not self.connected:
                return {'success': False, 'error_msg': '未连接'}

            # 参数验证
            if order_type not in ['buy', 'sell']:
                return {'success': False, 'error_msg': f'无效的订单类型: {order_type}'}

            if volume <= 0 or volume % 100 != 0:
                return {'success': False, 'error_msg': f'数量必须是100的整数倍: {volume}'}

            # 转换订单类型
            xt_order_type = xtconstant.STOCK_BUY if order_type == 'buy' else xtconstant.STOCK_SELL

            # 转换价格类型
            if price_type == 'market':
                xt_price_type = xtconstant.MARKET_SMART_ORDER  # 智能市价单
                xt_price = 0  # 市价单价格为0
            elif price_type == 'limit':
                xt_price_type = xtconstant.FIX_PRICE  # 限价单
                if price is None or price <= 0:
                    return {'success': False, 'error_msg': '限价单必须指定价格'}
                xt_price = price
            else:
                return {'success': False, 'error_msg': f'无效的价格类型: {price_type}'}

            # 同步下单
            order_id = self.trader.order_stock(
                self.account,
                stock_code,
                xt_order_type,
                volume,
                xt_price_type,
                xt_price,
                strategy_name,
                remark
            )

            if order_id:
                print(f"[XtTrader] 下单成功: {stock_code} {order_type} {volume}股 "
                      f"@{price if price else '市价'}, 订单ID={order_id}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'stock_code': stock_code,
                    'order_type': order_type,
                    'volume': volume,
                    'price': price
                }
            else:
                print(f"[XtTrader] 下单失败: {stock_code}")
                return {'success': False, 'error_msg': '下单失败，订单ID为空'}

        except Exception as e:
            error_msg = f"下单异常: {e}"
            print(f"[XtTrader] {error_msg}")
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
            if not self.connected:
                print("[XtTrader] 未连接，无法撤单")
                return False

            # 撤单
            result = self.trader.cancel_order(order_id)

            if result == 0:
                print(f"[XtTrader] 撤单成功: {order_id}")
                return True
            else:
                print(f"[XtTrader] 撤单失败: {order_id}, 错误码: {result}")
                return False

        except Exception as e:
            print(f"[XtTrader] 撤单异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def query_orders(self) -> List[Dict]:
        """
        查询委托

        返回:
            list: 委托列表
        """
        try:
            if not self.connected:
                print("[XtTrader] 未连接，无法查询委托")
                return []

            # 同步查询委托
            orders = self.trader.query_stock_orders(self.account)

            if not orders:
                print("[XtTrader] 无委托")
                return []

            result = []
            for order in orders:
                result.append({
                    'order_id': order.order_id,
                    'stock_code': order.stock_code,
                    'order_type': order.order_type,
                    'order_volume': order.order_volume,
                    'traded_volume': order.traded_volume,
                    'price_type': order.price_type,
                    'price': order.price,
                    'order_status': order.order_status,
                    'strategy_name': order.strategy_name,
                    'remark': order.remark
                })

            print(f"[XtTrader] 委托查询成功: 共{len(result)}条委托")
            return result

        except Exception as e:
            print(f"[XtTrader] 查询委托异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def __enter__(self):
        """支持上下文管理器"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.disconnect()


# 测试代码
if __name__ == '__main__':
    # 测试交易接口
    print("=" * 60)
    print("miniQMT交易接口测试")
    print("=" * 60)

    # 注意：需要修改为实际的账户ID
    test_account_id = "your_account_id"

    trader = XtTrader(account_id=test_account_id, session_id=123456)

    # 连接测试
    if trader.connect():
        print("\n✓ 连接成功")

        # 查询账户测试
        print("\n--- 查询账户 ---")
        account_info = trader.query_account()
        if account_info:
            print(f"总资产: {account_info['total_asset']:.2f}")
            print(f"可用资金: {account_info['cash']:.2f}")

        # 查询持仓测试
        print("\n--- 查询持仓 ---")
        positions = trader.query_positions()
        for pos in positions:
            print(f"{pos['stock_code']}: {pos['volume']}股")

        # 断开连接
        print("\n--- 断开连接 ---")
        trader.disconnect()
    else:
        print("\n✗ 连接失败")
