"""
自动化订单执行器
基于XtQuant实现ETF网格交易的自动化下单功能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import uuid

from config.settings import TradingConfig, Direction, OrderStatus, ETF_GRID_CONFIG
from data.xtquant_client import XtQuantClient
from utils.logger import get_logger

try:
    from xtquant import xttrader, xtconstant
    XTTRADER_AVAILABLE = True
except ImportError:
    XTTRADER_AVAILABLE = False

class OrderType(Enum):
    """订单类型"""
    LIMIT = "LIMIT"           # 限价单
    MARKET = "MARKET"         # 市价单
    STOP_LOSS = "STOP_LOSS"   # 止损单

@dataclass
class Order:
    """订单对象"""
    order_id: str
    symbol: str
    direction: str  # BUY/SELL
    order_type: str
    price: float
    quantity: int
    amount: float
    status: str = OrderStatus.PENDING
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    filled_quantity: int = 0
    filled_amount: float = 0.0
    avg_price: float = 0.0
    commission: float = 0.0
    error_message: str = ""
    xt_order_id: str = ""

@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    order_id: str
    message: str
    xt_order_id: str = ""
    error_code: int = 0

class ETFOrderExecutor:
    """ETF订单执行器"""

    def __init__(self, session_id: int = None):
        """
        初始化订单执行器

        Args:
            session_id: QMT会话ID
        """
        self.session_id = session_id or ETF_GRID_CONFIG.session_id
        self.logger = get_logger("ETFOrderExecutor")

        # 数据客户端
        self.data_client = None
        self.trader_client = None

        # 订单管理
        self.pending_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self._lock = threading.RLock()

        # 执行配置
        self.enable_simulation = False  # 是否启用模拟模式
        self.max_retry_count = 3
        self.retry_delay = 1.0

        # 统计信息
        self.execution_stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'total_commission': 0.0,
            'total_amount': 0.0
        }

        # 初始化连接
        self._initialize_clients()

        self.logger.info(f"ETF订单执行器初始化完成，会话ID: {self.session_id}")

    def _initialize_clients(self):
        """初始化客户端连接"""
        try:
            # 初始化数据客户端
            self.data_client = XtQuantClient(
                data_dir=ETF_GRID_CONFIG.qmt_data_dir,
                session_id=self.session_id
            )

            if not self.data_client.connect():
                raise Exception("数据客户端连接失败")

            # 初始化交易客户端
            if XTTRADER_AVAILABLE:
                connect_result = xttrader.connect()
                if connect_result != 0:
                    self.logger.warning("交易客户端连接失败，启用模拟模式")
                    self.enable_simulation = True
                else:
                    self.trader_client = xttrader
                    self.logger.info("交易客户端连接成功")
            else:
                self.logger.warning("XtQuant交易模块不可用，启用模拟模式")
                self.enable_simulation = True

        except Exception as e:
            self.logger.error(f"客户端初始化失败: {str(e)}")
            self.enable_simulation = True

    def place_order(self,
                   symbol: str,
                   direction: str,
                   quantity: int,
                   price: float = None,
                   order_type: str = OrderType.LIMIT) -> ExecutionResult:
        """
        下单

        Args:
            symbol: 股票代码
            direction: 买卖方向 BUY/SELL
            quantity: 数量
            price: 价格（限价单需要）
            order_type: 订单类型

        Returns:
            执行结果
        """
        try:
            # 验证参数
            if not self._validate_order_params(symbol, direction, quantity, price, order_type):
                return ExecutionResult(
                    success=False,
                    order_id="",
                    message="订单参数验证失败"
                )

            # 生成订单ID
            order_id = str(uuid.uuid4())

            # 计算订单金额
            amount = quantity * price if price else quantity * self._get_market_price(symbol)

            # 创建订单对象
            order = Order(
                order_id=order_id,
                symbol=symbol,
                direction=direction,
                order_type=order_type,
                price=price or 0.0,
                quantity=quantity,
                amount=amount
            )

            with self._lock:
                self.pending_orders[order_id] = order
                self.execution_stats['total_orders'] += 1

            # 执行下单
            if self.enable_simulation:
                result = self._simulate_order_execution(order)
            else:
                result = self._execute_real_order(order)

            # 更新订单状态
            if result.success:
                order.status = OrderStatus.SUBMITTED
                order.xt_order_id = result.xt_order_id
                self.execution_stats['successful_orders'] += 1
                self.execution_stats['total_amount'] += amount

                self.logger.info(f"订单提交成功: {direction} {quantity}股 {symbol} @¥{price:.3f}, "
                               f"订单ID: {order_id}")
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = result.message
                self.execution_stats['failed_orders'] += 1

                self.logger.error(f"订单提交失败: {result.message}")

            order.update_time = datetime.now()

            return result

        except Exception as e:
            self.logger.error(f"下单异常: {str(e)}")
            return ExecutionResult(
                success=False,
                order_id="",
                message=f"下单异常: {str(e)}"
            )

    def _validate_order_params(self,
                              symbol: str,
                              direction: str,
                              quantity: int,
                              price: float,
                              order_type: str) -> bool:
        """验证订单参数"""
        try:
            # 检查ETF是否在配置中
            if not ETF_GRID_CONFIG.is_valid_etf(symbol):
                self.logger.error(f"ETF不在有效范围内: {symbol}")
                return False

            # 检查方向
            if direction not in [Direction.BUY, Direction.SELL]:
                self.logger.error(f"无效的交易方向: {direction}")
                return False

            # 检查数量
            if quantity <= 0 or quantity % TradingConfig.MIN_TRADE_UNIT != 0:
                self.logger.error(f"无效的交易数量: {quantity}")
                return False

            # 检查价格（限价单需要价格）
            if order_type == OrderType.LIMIT and (price is None or price <= 0):
                self.logger.error(f"限价单需要有效价格: {price}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"订单参数验证异常: {str(e)}")
            return False

    def _get_market_price(self, symbol: str) -> float:
        """获取市场价格"""
        try:
            if self.data_client and self.data_client.is_connected:
                data = self.data_client.get_market_data([symbol], count=1)
                if data and symbol in data:
                    return float(data[symbol].get('close', 0))

            # 返回配置中的基准价格
            etf_config = ETF_GRID_CONFIG.get_etf_config(symbol)
            if etf_config:
                return etf_config['base_price']

            return 1.0

        except Exception as e:
            self.logger.error(f"获取市场价格失败: {str(e)}")
            return 1.0

    def _simulate_order_execution(self, order: Order) -> ExecutionResult:
        """模拟订单执行"""
        try:
            # 模拟订单ID
            simulated_order_id = f"SIM_{order.order_id[:8]}"

            # 模拟执行延迟
            time.sleep(0.1)

            # 模拟成功率（95%）
            import random
            if random.random() < 0.95:
                # 模拟成交
                order.status = OrderStatus.FILLED
                order.filled_quantity = order.quantity
                order.filled_amount = order.amount
                order.avg_price = order.price

                # 计算手续费
                commission = max(order.amount * TradingConfig.COMMISSION_RATE, TradingConfig.MIN_COMMISSION)
                order.commission = commission

                # 移动到历史记录
                with self._lock:
                    if order.order_id in self.pending_orders:
                        del self.pending_orders[order.order_id]
                    self.order_history.append(order)

                return ExecutionResult(
                    success=True,
                    order_id=order.order_id,
                    message="模拟成交成功",
                    xt_order_id=simulated_order_id
                )
            else:
                # 模拟失败
                return ExecutionResult(
                    success=False,
                    order_id=order.order_id,
                    message="模拟执行失败",
                    error_code=-1
                )

        except Exception as e:
            self.logger.error(f"模拟订单执行异常: {str(e)}")
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                message=f"模拟执行异常: {str(e)}"
            )

    def _execute_real_order(self, order: Order) -> ExecutionResult:
        """执行真实订单"""
        try:
            if not self.trader_client:
                raise Exception("交易客户端未连接")

            # 转换交易参数
            xt_direction = xtconstant.STOCK_BUY if order.direction == Direction.BUY else xtconstant.STOCK_SELL
            xt_order_type = xtconstant.FIX_PRICE if order.order_type == OrderType.LIMIT else xtconstant.MARKET_PRICE

            # 下单参数
            order_param = {
                'stock_code': order.symbol,
                'direction': xt_direction,
                'order_type': xt_order_type,
                'price': order.price,
                'volume': order.quantity,
                'order_remark': f'ETF网格交易_{order.order_id[:8]}',
                'session_id': self.session_id
            }

            # 执行下单
            xt_order_id = xttrader.order_stock(**order_param)

            if xt_order_id and xt_order_id > 0:
                return ExecutionResult(
                    success=True,
                    order_id=order.order_id,
                    message="订单提交成功",
                    xt_order_id=str(xt_order_id)
                )
            else:
                return ExecutionResult(
                    success=False,
                    order_id=order.order_id,
                    message="订单提交失败",
                    error_code=xt_order_id or -1
                )

        except Exception as e:
            self.logger.error(f"真实订单执行异常: {str(e)}")
            return ExecutionResult(
                success=False,
                order_id=order.order_id,
                message=f"执行异常: {str(e)}"
            )

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        try:
            with self._lock:
                if order_id not in self.pending_orders:
                    self.logger.warning(f"订单不存在或已完成: {order_id}")
                    return False

                order = self.pending_orders[order_id]

            if self.enable_simulation:
                # 模拟撤单
                order.status = OrderStatus.CANCELLED
                with self._lock:
                    del self.pending_orders[order_id]
                    self.order_history.append(order)

                self.logger.info(f"模拟撤单成功: {order_id}")
                return True

            elif self.trader_client and order.xt_order_id:
                # 真实撤单
                cancel_result = xttrader.cancel_stock(order.xt_order_id)

                if cancel_result == 0:
                    order.status = OrderStatus.CANCELLED
                    with self._lock:
                        del self.pending_orders[order_id]
                        self.order_history.append(order)

                    self.logger.info(f"撤单成功: {order_id}")
                    return True
                else:
                    self.logger.error(f"撤单失败: {order_id}, 错误码: {cancel_result}")
                    return False

        except Exception as e:
            self.logger.error(f"撤单异常: {order_id}, 错误: {str(e)}")
            return False

    def query_order_status(self, order_id: str) -> Optional[Order]:
        """查询订单状态"""
        try:
            with self._lock:
                # 先在待处理订单中查找
                if order_id in self.pending_orders:
                    order = self.pending_orders[order_id]

                    # 如果是真实交易，查询最新状态
                    if not self.enable_simulation and self.trader_client and order.xt_order_id:
                        self._update_real_order_status(order)

                    return order

                # 在历史订单中查找
                for order in self.order_history:
                    if order.order_id == order_id:
                        return order

            return None

        except Exception as e:
            self.logger.error(f"查询订单状态异常: {order_id}, 错误: {str(e)}")
            return None

    def _update_real_order_status(self, order: Order):
        """更新真实订单状态"""
        try:
            if not self.trader_client or not order.xt_order_id:
                return

            # 查询订单状态
            order_status = xttrader.query_stock_order(order.xt_order_id)

            if order_status:
                # 更新订单信息
                order.filled_quantity = order_status.get('volume', 0)
                order.filled_amount = order_status.get('amount', 0)
                order.avg_price = order_status.get('price', 0)
                order.commission = order_status.get('commission', 0)

                # 更新状态
                if order_status.get('status') == 2:  # 已成交
                    order.status = OrderStatus.FILLED
                elif order_status.get('status') == 3:  # 已撤单
                    order.status = OrderStatus.CANCELLED
                elif order_status.get('status') == 4:  # 已拒绝
                    order.status = OrderStatus.REJECTED

                order.update_time = datetime.now()

                # 如果订单已完成，移动到历史记录
                if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                    with self._lock:
                        if order.order_id in self.pending_orders:
                            del self.pending_orders[order.order_id]
                        self.order_history.append(order)

        except Exception as e:
            self.logger.error(f"更新真实订单状态异常: {order.order_id}, 错误: {str(e)}")

    def get_pending_orders(self) -> List[Order]:
        """获取待处理订单"""
        with self._lock:
            return list(self.pending_orders.values())

    def get_order_history(self, limit: int = 100) -> List[Order]:
        """获取历史订单"""
        with self._lock:
            return self.order_history[-limit:] if limit > 0 else self.order_history.copy()

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        with self._lock:
            stats = self.execution_stats.copy()
            stats['pending_orders_count'] = len(self.pending_orders)
            stats['history_orders_count'] = len(self.order_history)

            if stats['total_orders'] > 0:
                stats['success_rate'] = stats['successful_orders'] / stats['total_orders']
            else:
                stats['success_rate'] = 0.0

            return stats

    def place_grid_orders(self, signals: List[Dict[str, Any]]) -> List[ExecutionResult]:
        """
        批量执行网格订单

        Args:
            signals: 交易信号列表

        Returns:
            执行结果列表
        """
        results = []

        for signal in signals:
            try:
                result = self.place_order(
                    symbol=signal['symbol'],
                    direction=signal['action'],
                    quantity=signal['quantity'],
                    price=signal['price'],
                    order_type=OrderType.LIMIT
                )

                results.append(result)

                # 添加延迟避免过快的订单提交
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"执行网格订单失败: {str(e)}")
                results.append(ExecutionResult(
                    success=False,
                    order_id="",
                    message=f"执行失败: {str(e)}"
                ))

        return results

    def cleanup_expired_orders(self):
        """清理过期订单"""
        try:
            current_time = datetime.now()
            expired_orders = []

            with self._lock:
                for order_id, order in list(self.pending_orders.items()):
                    # 订单超过5分钟自动取消
                    if (current_time - order.create_time).seconds > 300:
                        expired_orders.append(order_id)

            for order_id in expired_orders:
                self.cancel_order(order_id)

            if expired_orders:
                self.logger.info(f"清理过期订单: {len(expired_orders)}个")

        except Exception as e:
            self.logger.error(f"清理过期订单异常: {str(e)}")

    def __del__(self):
        """析构函数"""
        try:
            # 清理待处理订单
            pending_orders = self.get_pending_orders()
            for order in pending_orders:
                self.cancel_order(order.order_id)

        except Exception:
            pass