"""
ETF网格交易引擎
基于Table.xls配置实现ETF网格交易策略的核心逻辑
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import math

from config.settings import TradingConfig, Direction, OrderStatus, ETF_GRID_CONFIG
from config.risk_params import RiskManagerConfig, GRID_RISK_PARAMS
from utils.logger import get_logger
from utils.helpers import safe_divide, round_to_nearest

class GridLevelType(Enum):
    """网格等级类型"""
    BUY = "BUY"     # 买入网格
    SELL = "SELL"   # 卖出网格

@dataclass
class GridLevel:
    """网格等级"""
    level: int                   # 网格等级（0为基准）
    price: float                 # 网格价格
    type: GridLevelType          # 网格类型
    quantity: int = 0            # 计划交易数量
    filled_quantity: int = 0     # 已成交数量
    status: str = "PENDING"      # 状态
    created_time: datetime = field(default_factory=datetime.now)
    filled_time: Optional[datetime] = None
    order_id: Optional[str] = None

@dataclass
class GridPosition:
    """网格持仓"""
    symbol: str
    quantity: int
    avg_price: float
    cost_basis: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    grid_levels: List[GridLevel] = field(default_factory=list)

class GridEngine:
    """网格交易引擎"""

    def __init__(self, symbol: str, capital: float, config: Dict[str, Any] = None):
        """
        初始化网格交易引擎

        Args:
            symbol: 交易标的
            capital: 分配资金
            config: 配置参数
        """
        self.symbol = symbol
        self.capital = capital
        self.config = config or self._get_default_config()

        self.logger = get_logger(f"GridEngine_{symbol}")

        # 网格参数
        self.grid_levels = config.get('grid_levels', TradingConfig.DEFAULT_GRID_LEVELS)
        self.grid_spacing_pct = config.get('grid_spacing_pct', TradingConfig.DEFAULT_GRID_SPACING_PCT)
        self.reference_price = 0.0
        self.position_size_pct = config.get('position_size_pct', 0.05)

        # 网格状态
        self.grid_levels_list: List[GridLevel] = []
        self.current_price = 0.0
        self.grid_center = 0.0
        self.last_rebalance_time = None

        # 持仓管理
        self.positions: Dict[str, GridPosition] = {}
        self.total_position_value = 0.0
        self.available_capital = capital

        # 风险控制
        self.risk_limits = RiskManagerConfig.get_current_limits()
        self.grid_risk_params = GRID_RISK_PARAMS

        # 运行状态
        self.active = False
        self._lock = threading.RLock()

        # 统计信息
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_commission': 0.0,
            'realized_pnl': 0.0,
            'grid_efficiency': 0.0,
            'last_trade_time': None
        }

        self.logger.info(f"网格交易引擎初始化完成: {symbol}, 资金: {capital:,.2f}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'grid_levels': TradingConfig.DEFAULT_GRID_LEVELS,
            'grid_spacing_pct': TradingConfig.DEFAULT_GRID_SPACING_PCT,
            'position_size_pct': self.risk_limits.position_size_pct,
            'reference_period': TradingConfig.DEFAULT_REFERENCE_PERIOD,
            'rebalance_threshold': TradingConfig.DEFAULT_REBALANCE_THRESHOLD,
        }

    def initialize_grid(self, reference_price: float, historical_prices: pd.Series = None) -> bool:
        """
        初始化网格

        Args:
            reference_price: 基准价格
            historical_prices: 历史价格数据（用于计算动态间距）

        Returns:
            初始化是否成功
        """
        with self._lock:
            try:
                self.reference_price = reference_price
                self.grid_center = reference_price

                # 计算网格间距
                if historical_prices is not None and len(historical_prices) > 20:
                    volatility = historical_prices.pct_change().std()
                    dynamic_spacing = min(max(volatility * 2, 0.01), 0.05)
                    grid_spacing = min(self.grid_spacing_pct, dynamic_spacing)
                    self.logger.info(f"使用动态网格间距: {grid_spacing:.3f}")
                else:
                    grid_spacing = self.grid_spacing_pct

                # 清空现有网格
                self.grid_levels_list.clear()

                # 生成网格等级
                upper_levels = self.grid_levels // 2
                lower_levels = self.grid_levels - upper_levels

                # 生成买入网格（下方）
                for i in range(lower_levels, 0, -1):
                    price = reference_price * (1 - grid_spacing * i)
                    grid_level = GridLevel(
                        level=-i,
                        price=round_to_nearest(price),
                        type=GridLevelType.BUY,
                        quantity=self._calculate_grid_quantity(price)
                    )
                    self.grid_levels_list.append(grid_level)

                # 生成卖出网格（上方）
                for i in range(1, upper_levels + 1):
                    price = reference_price * (1 + grid_spacing * i)
                    grid_level = GridLevel(
                        level=i,
                        price=round_to_nearest(price),
                        type=GridLevelType.SELL,
                        quantity=self._calculate_grid_quantity(price)
                    )
                    self.grid_levels_list.append(grid_level)

                # 按价格排序
                self.grid_levels_list.sort(key=lambda x: x.price)

                self.active = True
                self.last_rebalance_time = datetime.now()

                self.logger.info(f"网格初始化完成: 基准价={reference_price:.3f}, "
                               f"间距={grid_spacing:.3f}, 等级数={len(self.grid_levels_list)}")

                return True

            except Exception as e:
                self.logger.error(f"网格初始化失败: {str(e)}")
                return False

    def _calculate_grid_quantity(self, price: float) -> int:
        """计算网格交易数量"""
        position_value = self.capital * self.position_size_pct
        shares = int(position_value / price)

        # 调整到最小交易单位的整数倍
        min_unit = TradingConfig.MIN_TRADE_UNIT
        shares = (shares // min_unit) * min_unit

        return max(shares, min_unit)

    def update_price(self, price: float, timestamp: datetime = None) -> List[GridLevel]:
        """
        更新价格并检查网格触发

        Args:
            price: 当前价格
            timestamp: 时间戳

        Returns:
            触发的网格列表
        """
        if timestamp is None:
            timestamp = datetime.now()

        with self._lock:
            if not self.active:
                return []

            self.current_price = price
            triggered_levels = []

            # 检查是否需要重新平衡
            if self._should_rebalance(price):
                self._rebalance_grid(price)

            # 检查网格触发
            for grid_level in self.grid_levels_list:
                if grid_level.status == "PENDING" and self._is_grid_triggered(grid_level, price):
                    triggered_levels.append(grid_level)
                    grid_level.status = "TRIGGERED"
                    grid_level.created_time = timestamp

            return triggered_levels

    def _is_grid_triggered(self, grid_level: GridLevel, price: float) -> bool:
        """检查网格是否被触发"""
        if grid_level.type == GridLevelType.BUY:
            return price <= grid_level.price
        elif grid_level.type == GridLevelType.SELL:
            return price >= grid_level.price
        return False

    def _should_rebalance(self, price: float) -> bool:
        """检查是否需要重新平衡"""
        if self.last_rebalance_time is None:
            return True

        # 检查时间间隔
        time_since_rebalance = datetime.now() - self.last_rebalance_time
        if time_since_rebalance.days >= 7:  # 每周重新平衡
            return True

        # 检查价格偏离
        price_deviation = abs(price - self.grid_center) / self.grid_center
        rebalance_threshold = self.config.get('rebalance_threshold', 0.15)

        return price_deviation >= rebalance_threshold

    def _rebalance_grid(self, current_price: float):
        """重新平衡网格"""
        self.logger.info(f"重新平衡网格: 当前价格={current_price:.3f}, 中心价格={self.grid_center:.3f}")

        # 重置已完成的网格
        for grid_level in self.grid_levels_list:
            if grid_level.status in ["FILLED", "CANCELLED"]:
                grid_level.status = "PENDING"
                grid_level.filled_quantity = 0
                grid_level.filled_time = None
                grid_level.order_id = None

        # 更新网格中心
        self.grid_center = current_price

        # 重新计算网格价格（保持相对间距）
        grid_spacing = self.grid_spacing_pct
        upper_levels = self.grid_levels // 2
        lower_levels = self.grid_levels - upper_levels

        # 更新买入网格价格
        for i, grid_level in enumerate(self.grid_levels_list):
            if grid_level.level < 0:  # 买入网格
                new_price = current_price * (1 - grid_spacing * abs(grid_level.level))
                grid_level.price = round_to_nearest(new_price)
                grid_level.quantity = self._calculate_grid_quantity(new_price)

        # 更新卖出网格价格
        for i, grid_level in enumerate(self.grid_levels_list):
            if grid_level.level > 0:  # 卖出网格
                new_price = current_price * (1 + grid_spacing * abs(grid_level.level))
                grid_level.price = round_to_nearest(new_price)
                grid_level.quantity = self._calculate_grid_quantity(new_price)

        self.last_rebalance_time = datetime.now()
        self.logger.info(f"网格重新平衡完成")

    def execute_grid_level(self, grid_level: GridLevel, order_id: str) -> bool:
        """
        执行网格交易

        Args:
            grid_level: 网格等级
            order_id: 订单ID

        Returns:
            执行是否成功
        """
        with self._lock:
            try:
                # 更新网格状态
                grid_level.order_id = order_id
                grid_level.status = "SUBMITTED"

                # 更新持仓（模拟执行）
                if grid_level.type == GridLevelType.BUY:
                    self._execute_buy_grid(grid_level)
                else:
                    self._execute_sell_grid(grid_level)

                self.stats['total_trades'] += 1
                self.stats['last_trade_time'] = datetime.now()

                self.logger.info(f"网格执行: {grid_level.type.value} "
                               f"{grid_level.quantity}股 @¥{grid_level.price:.3f}")

                return True

            except Exception as e:
                self.logger.error(f"网格执行失败: {str(e)}")
                grid_level.status = "FAILED"
                return False

    def _execute_buy_grid(self, grid_level: GridLevel):
        """执行买入网格"""
        trade_value = grid_level.quantity * grid_level.price
        commission = max(trade_value * TradingConfig.COMMISSION_RATE, TradingConfig.MIN_COMMISSION)

        if trade_value + commission > self.available_capital:
            self.logger.warning(f"资金不足: 需要{trade_value + commission:.2f}, 可用{self.available_capital:.2f}")
            return

        # 更新持仓
        if self.symbol not in self.positions:
            self.positions[self.symbol] = GridPosition(
                symbol=self.symbol,
                quantity=0,
                avg_price=0.0,
                cost_basis=0.0
            )

        position = self.positions[self.symbol]
        old_quantity = position.quantity
        old_cost = position.cost_basis

        # 计算新的平均价格
        new_quantity = old_quantity + grid_level.quantity
        new_cost = old_cost + trade_value
        new_avg_price = new_cost / new_quantity if new_quantity > 0 else 0.0

        position.quantity = new_quantity
        position.avg_price = new_avg_price
        position.cost_basis = new_cost
        position.grid_levels.append(grid_level)

        # 更新资金
        self.available_capital -= (trade_value + commission)
        self.total_position_value += trade_value

        # 更新统计
        self.stats['total_commission'] += commission

    def _execute_sell_grid(self, grid_level: GridLevel):
        """执行卖出网格"""
        if self.symbol not in self.positions:
            self.logger.warning(f"无持仓可卖出: {self.symbol}")
            return

        position = self.positions[self.symbol]
        if position.quantity < grid_level.quantity:
            self.logger.warning(f"持仓不足: 需要{grid_level.quantity}, 持有{position.quantity}")
            return

        trade_value = grid_level.quantity * grid_level.price
        commission = max(trade_value * TradingConfig.COMMISSION_RATE, TradingConfig.MIN_COMMISSION)

        # 计算盈亏
        sell_cost_basis = position.avg_price * grid_level.quantity
        realized_pnl = trade_value - sell_cost_basis - commission

        # 更新持仓
        position.quantity -= grid_level.quantity
        position.realized_pnl += realized_pnl

        if position.quantity == 0:
            position.cost_basis = 0.0
            position.avg_price = 0.0
        else:
            position.cost_basis -= sell_cost_basis

        # 更新资金
        self.available_capital += (trade_value - commission)
        self.total_position_value -= trade_value

        # 更新统计
        self.stats['total_commission'] += commission
        self.stats['realized_pnl'] += realized_pnl

        if realized_pnl > 0:
            self.stats['winning_trades'] += 1
        else:
            self.stats['losing_trades'] += 1

    def update_market_data(self, price: float):
        """更新市场数据"""
        with self._lock:
            self.current_price = price

            # 计算未实现盈亏
            if self.symbol in self.positions:
                position = self.positions[self.symbol]
                if position.quantity > 0:
                    position.unrealized_pnl = (price - position.avg_price) * position.quantity

    def get_pending_levels(self) -> List[GridLevel]:
        """获取待执行的网格"""
        return [level for level in self.grid_levels_list if level.status == "PENDING"]

    def get_triggered_levels(self) -> List[GridLevel]:
        """获取已触发的网格"""
        return [level for level in self.grid_levels_list if level.status == "TRIGGERED"]

    def get_filled_levels(self) -> List[GridLevel]:
        """获取已成交的网格"""
        return [level for level in self.grid_levels_list if level.status == "FILLED"]

    def calculate_performance(self) -> Dict[str, Any]:
        """计算网格策略表现"""
        with self._lock:
            total_pnl = self.stats['realized_pnl']
            if self.symbol in self.positions:
                total_pnl += self.positions[self.symbol].unrealized_pnl

            total_return = safe_divide(total_pnl, self.capital)
            win_rate = safe_divide(self.stats['winning_trades'], self.stats['total_trades'])

            # 计算网格效率
            filled_levels = len(self.get_filled_levels())
            total_levels = len(self.grid_levels_list)
            grid_efficiency = safe_divide(filled_levels, total_levels) if total_levels > 0 else 0

            return {
                'total_return': total_return,
                'total_pnl': total_pnl,
                'realized_pnl': self.stats['realized_pnl'],
                'unrealized_pnl': self.positions.get(self.symbol, GridPosition('', 0, 0, 0)).unrealized_pnl,
                'win_rate': win_rate,
                'total_trades': self.stats['total_trades'],
                'grid_efficiency': grid_efficiency,
                'current_position': self.positions.get(self.symbol, GridPosition('', 0, 0, 0)).quantity,
                'available_capital': self.available_capital,
                'total_commission': self.stats['total_commission']
            }

    def get_grid_status(self) -> Dict[str, Any]:
        """获取网格状态"""
        with self._lock:
            pending_count = len(self.get_pending_levels())
            triggered_count = len(self.get_triggered_levels())
            filled_count = len(self.get_filled_levels())

            return {
                'active': self.active,
                'symbol': self.symbol,
                'current_price': self.current_price,
                'reference_price': self.reference_price,
                'grid_center': self.grid_center,
                'total_levels': len(self.grid_levels_list),
                'pending_levels': pending_count,
                'triggered_levels': triggered_count,
                'filled_levels': filled_count,
                'last_rebalance': self.last_rebalance_time,
                'performance': self.calculate_performance()
            }

    def reset_grid(self):
        """重置网格"""
        with self._lock:
            self.active = False
            self.grid_levels_list.clear()
            self.positions.clear()
            self.current_price = 0.0
            self.grid_center = 0.0
            self.available_capital = self.capital
            self.total_position_value = 0.0

            # 重置统计
            self.stats = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_commission': 0.0,
                'realized_pnl': 0.0,
                'grid_efficiency': 0.0,
                'last_trade_time': None
            }

            self.logger.info("网格已重置")


class ETFGridStrategy:
    """ETF网格交易策略类"""

    def __init__(self, etf_code: str, capital: float = 100000):
        """
        初始化ETF网格交易策略

        Args:
            etf_code: ETF代码
            capital: 分配资金
        """
        self.etf_code = etf_code
        self.capital = capital
        self.logger = get_logger(f"ETFGridStrategy_{etf_code}")

        # 获取ETF配置
        self.etf_config = ETF_GRID_CONFIG.get_etf_config(etf_code)
        if not self.etf_config:
            raise ValueError(f"未找到ETF配置: {etf_code}")

        # 初始化网格引擎
        grid_config = {
            'grid_levels': len(self.etf_config['grid_levels']),
            'grid_spacing_pct': self.etf_config['up_trigger'],  # 使用上涨触发比例作为网格间距
            'position_size_pct': 0.1,
            'reference_period': 20,
            'rebalance_threshold': 0.15
        }

        self.grid_engine = GridEngine(etf_code, capital, grid_config)

        # 策略参数
        self.base_price = self.etf_config['base_price']
        self.up_trigger = self.etf_config['up_trigger']
        self.down_trigger = self.etf_config['down_trigger']
        self.buy_amount = self.etf_config['buy_amount']
        self.sell_amount = self.etf_config['sell_amount']
        self.valid_until = datetime.strptime(self.etf_config['valid_until'], "%Y-%m-%d")

        # 运行状态
        self.is_running = False
        self.last_price = 0.0
        self.last_update_time = None

        # 统计信息
        self.performance_stats = {
            'start_time': None,
            'total_trades': 0,
            'buy_trades': 0,
            'sell_trades': 0,
            'total_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_commission': 0.0
        }

        self.logger.info(f"ETF网格策略初始化完成: {etf_code}({self.etf_config['etf_name']}), "
                        f"基准价: {self.base_price}, 资金: {capital:,.2f}")

    def initialize(self, current_price: float = None) -> bool:
        """
        初始化策略

        Args:
            current_price: 当前价格（如果为None，使用基准价格）

        Returns:
            初始化是否成功
        """
        try:
            # 检查ETF是否仍在有效期内
            if datetime.now() > self.valid_until:
                self.logger.error(f"ETF已过期: {self.etf_code}, 有效期至: {self.valid_until}")
                return False

            # 确定初始价格
            reference_price = current_price if current_price else self.base_price
            if reference_price <= 0:
                self.logger.error(f"无效的参考价格: {reference_price}")
                return False

            # 初始化网格
            success = self.grid_engine.initialize_grid(reference_price)
            if success:
                self.last_price = reference_price
                self.last_update_time = datetime.now()
                self.logger.info(f"策略初始化成功: 参考价格 {reference_price:.3f}")

            return success

        except Exception as e:
            self.logger.error(f"策略初始化失败: {str(e)}")
            return False

    def update_price(self, price: float, timestamp: datetime = None) -> List[Dict[str, Any]]:
        """
        更新价格并生成交易信号

        Args:
            price: 当前价格
            timestamp: 时间戳

        Returns:
            交易信号列表
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.last_price = price
        self.last_update_time = timestamp

        if not self.is_running:
            return []

        # 检查价格有效性
        if price <= 0:
            self.logger.warning(f"无效价格: {price}")
            return []

        try:
            # 更新网格引擎
            triggered_levels = self.grid_engine.update_price(price, timestamp)

            # 转换为交易信号
            signals = []
            for level in triggered_levels:
                signal = self._create_signal(level, price, timestamp)
                if signal:
                    signals.append(signal)

            return signals

        except Exception as e:
            self.logger.error(f"价格更新失败: {str(e)}")
            return []

    def _create_signal(self, grid_level: 'GridLevel', current_price: float, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """创建交易信号"""
        try:
            # 根据网格类型创建信号
            if grid_level.type == GridLevelType.BUY:
                # 买入信号
                amount = self.buy_amount
                quantity = int(amount / current_price / 100) * 100  # 调整为手数

                signal = {
                    'symbol': self.etf_code,
                    'action': 'BUY',
                    'price': grid_level.price,
                    'quantity': quantity,
                    'amount': amount,
                    'trigger_type': 'GRID_BUY',
                    'grid_level': grid_level.level,
                    'timestamp': timestamp,
                    'confidence': 0.8,
                    'metadata': {
                        'etf_name': self.etf_config['etf_name'],
                        'base_price': self.base_price,
                        'trigger_ratio': self.down_trigger * abs(grid_level.level)
                    }
                }

            elif grid_level.type == GridLevelType.SELL:
                # 卖出信号
                amount = self.sell_amount
                quantity = int(amount / current_price / 100) * 100

                signal = {
                    'symbol': self.etf_code,
                    'action': 'SELL',
                    'price': grid_level.price,
                    'quantity': quantity,
                    'amount': amount,
                    'trigger_type': 'GRID_SELL',
                    'grid_level': grid_level.level,
                    'timestamp': timestamp,
                    'confidence': 0.8,
                    'metadata': {
                        'etf_name': self.etf_config['etf_name'],
                        'base_price': self.base_price,
                        'trigger_ratio': self.up_trigger * abs(grid_level.level)
                    }
                }

            else:
                return None

            self.logger.info(f"生成{signal['action']}信号: {signal['quantity']}股 @¥{signal['price']:.3f}")
            return signal

        except Exception as e:
            self.logger.error(f"创建交易信号失败: {str(e)}")
            return None

    def execute_trade(self, signal: Dict[str, Any], order_id: str) -> bool:
        """
        执行交易

        Args:
            signal: 交易信号
            order_id: 订单ID

        Returns:
            执行是否成功
        """
        try:
            # 这里可以连接到实际的交易系统
            # 目前先在网格引擎中模拟执行

            # 更新统计
            self.performance_stats['total_trades'] += 1
            if signal['action'] == 'BUY':
                self.performance_stats['buy_trades'] += 1
            else:
                self.performance_stats['sell_trades'] += 1

            # 计算手续费
            trade_value = signal['amount']
            commission = max(trade_value * TradingConfig.COMMISSION_RATE, TradingConfig.MIN_COMMISSION)
            self.performance_stats['total_commission'] += commission

            self.logger.info(f"执行交易: {signal['action']} {signal['quantity']}股 @¥{signal['price']:.3f}, "
                           f"订单ID: {order_id}")

            return True

        except Exception as e:
            self.logger.error(f"交易执行失败: {str(e)}")
            return False

    def start(self) -> bool:
        """启动策略"""
        if self.is_running:
            self.logger.warning("策略已在运行中")
            return True

        try:
            self.is_running = True
            self.performance_stats['start_time'] = datetime.now()

            self.logger.info(f"ETF网格策略已启动: {self.etf_code}")
            return True

        except Exception as e:
            self.logger.error(f"策略启动失败: {str(e)}")
            return False

    def stop(self):
        """停止策略"""
        if not self.is_running:
            return

        self.is_running = False
        self.logger.info(f"ETF网格策略已停止: {self.etf_code}")

    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        grid_status = self.grid_engine.get_grid_status()
        performance = self.grid_engine.calculate_performance()

        return {
            'etf_code': self.etf_code,
            'etf_name': self.etf_config['etf_name'],
            'is_running': self.is_running,
            'last_price': self.last_price,
            'last_update': self.last_update_time,
            'valid_until': self.valid_until,
            'base_price': self.base_price,
            'grid_status': grid_status,
            'performance': performance,
            'strategy_stats': self.performance_stats
        }

    def calculate_daily_pnl(self) -> float:
        """计算当日盈亏"""
        try:
            performance = self.grid_engine.calculate_performance()
            return performance.get('total_pnl', 0.0)
        except Exception as e:
            self.logger.error(f"计算当日盈亏失败: {str(e)}")
            return 0.0

    def check_risk_limits(self) -> Dict[str, Any]:
        """检查风险限制"""
        try:
            risk_check = {
                'within_limits': True,
                'warnings': [],
                'errors': []
            }

            # 检查最大损失
            daily_pnl = self.calculate_daily_pnl()
            max_loss = self.capital * 0.02  # 单日最大损失2%

            if daily_pnl < -max_loss:
                risk_check['within_limits'] = False
                risk_check['errors'].append(f"单日损失超限: {daily_pnl:.2f} > {max_loss:.2f}")

            # 检查仓位限制
            position_ratio = self.grid_engine.total_position_value / self.capital
            max_position_ratio = 0.8  # 最大仓位80%

            if position_ratio > max_position_ratio:
                risk_check['warnings'].append(f"仓位比例过高: {position_ratio:.2%}")

            # 检查有效期
            if datetime.now() > self.valid_until:
                risk_check['within_limits'] = False
                risk_check['errors'].append(f"ETF已过期: {self.valid_until}")

            return risk_check

        except Exception as e:
            self.logger.error(f"风险检查失败: {str(e)}")
            return {'within_limits': False, 'errors': [str(e)], 'warnings': []}

    def reset(self):
        """重置策略"""
        self.stop()
        self.grid_engine.reset_grid()
        self.last_price = 0.0
        self.last_update_time = None

        # 重置统计
        self.performance_stats = {
            'start_time': None,
            'total_trades': 0,
            'buy_trades': 0,
            'sell_trades': 0,
            'total_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_commission': 0.0
        }

        self.logger.info(f"ETF网格策略已重置: {self.etf_code}")