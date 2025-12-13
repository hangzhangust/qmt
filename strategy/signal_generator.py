"""
信号生成器
基于网格交易策略生成交易信号
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import time

from config.settings import Direction, OrderStatus
from config.risk_params import RiskManagerConfig, MarketRiskParams
from utils.logger import get_logger
from utils.helpers import safe_divide
from .grid_engine import GridEngine, GridLevel

class SignalType(Enum):
    """信号类型"""
    GRID_BUY = "GRID_BUY"           # 网格买入信号
    GRID_SELL = "GRID_SELL"         # 网格卖出信号
    REBALANCE = "REBALANCE"         # 重新平衡信号
    STOP_LOSS = "STOP_LOSS"         # 止损信号
    TAKE_PROFIT = "TAKE_PROFIT"     # 止盈信号
    EMERGENCY_EXIT = "EMERGENCY_EXIT" # 紧急退出信号

class SignalStrength(Enum):
    """信号强度"""
    WEAK = 1
    NORMAL = 2
    STRONG = 3
    URGENT = 4

@dataclass
class TradingSignal:
    """交易信号"""
    symbol: str
    signal_type: SignalType
    direction: Direction
    quantity: int
    price: float
    strength: SignalStrength
    timestamp: datetime
    source: str                    # 信号来源
    reason: str                    # 信号原因
    metadata: Dict[str, Any] = None  # 额外元数据
    order_id: Optional[str] = None
    status: str = "PENDING"

@dataclass
class MarketCondition:
    """市场状况"""
    trend: str = "NEUTRAL"          # 趋势方向
    volatility: float = 0.0         # 波动率
    momentum: float = 0.0           # 动量
    support_level: float = 0.0      # 支撑位
    resistance_level: float = 0.0   # 阻力位
    volume_ratio: float = 1.0       # 成交量比率

class SignalGenerator:
    """信号生成器"""

    def __init__(self, risk_manager=None):
        """
        初始化信号生成器

        Args:
            risk_manager: 风险管理器实例
        """
        self.logger = get_logger("SignalGenerator")
        self.risk_manager = risk_manager

        # 信号过滤器
        self.signal_filters = []
        self.signal_handlers = []

        # 信号历史
        self.signal_history: List[TradingSignal] = []
        self.max_history_size = 1000

        # 市场状况缓存
        self.market_conditions: Dict[str, MarketCondition] = {}

        # 信号统计
        self.stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'executed_signals': 0,
            'rejected_signals': 0,
            'last_signal_time': None
        }

        # 线程安全
        self._lock = threading.RLock()

        self.logger.info("信号生成器初始化完成")

    def add_signal_filter(self, filter_func: Callable[[TradingSignal], bool]):
        """
        添加信号过滤器

        Args:
            filter_func: 过滤函数，返回True表示信号有效
        """
        self.signal_filters.append(filter_func)
        self.logger.debug(f"添加信号过滤器: {filter_func.__name__}")

    def add_signal_handler(self, handler_func: Callable[[TradingSignal], None]):
        """
        添加信号处理器

        Args:
            handler_func: 处理函数
        """
        self.signal_handlers.append(handler_func)
        self.logger.debug(f"添加信号处理器: {handler_func.__name__}")

    def generate_grid_signals(self, grid_engine: GridEngine, current_price: float,
                            timestamp: datetime = None) -> List[TradingSignal]:
        """
        基于网格引擎生成交易信号

        Args:
            grid_engine: 网格交易引擎
            current_price: 当前价格
            timestamp: 时间戳

        Returns:
            交易信号列表
        """
        if timestamp is None:
            timestamp = datetime.now()

        signals = []

        try:
            # 更新网格引擎价格
            triggered_levels = grid_engine.update_price(current_price, timestamp)

            # 为每个触发的网格生成信号
            for grid_level in triggered_levels:
                signal = self._create_grid_signal(grid_level, grid_engine.symbol, timestamp)
                if signal:
                    signals.append(signal)

            # 检查重新平衡信号
            rebalance_signal = self._check_rebalance_signal(grid_engine, current_price, timestamp)
            if rebalance_signal:
                signals.append(rebalance_signal)

            # 检查风险信号
            risk_signals = self._check_risk_signals(grid_engine, current_price, timestamp)
            signals.extend(risk_signals)

        except Exception as e:
            self.logger.error(f"生成网格信号失败: {str(e)}")

        # 过滤和处理信号
        filtered_signals = self._filter_signals(signals)
        self._process_signals(filtered_signals)

        return filtered_signals

    def _create_grid_signal(self, grid_level: GridLevel, symbol: str,
                           timestamp: datetime) -> Optional[TradingSignal]:
        """创建网格交易信号"""
        try:
            # 确定信号方向
            if grid_level.type.value == "BUY":
                direction = Direction.BUY
                signal_type = SignalType.GRID_BUY
            else:
                direction = Direction.SELL
                signal_type = SignalType.GRID_SELL

            # 确定信号强度
            strength = self._calculate_signal_strength(grid_level)

            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                direction=direction,
                quantity=grid_level.quantity,
                price=grid_level.price,
                strength=strength,
                timestamp=timestamp,
                source="GridEngine",
                reason=f"网格等级 {grid_level.level} 触发",
                metadata={
                    'grid_level': grid_level.level,
                    'grid_type': grid_level.type.value,
                    'original_price': grid_level.price
                }
            )

            self.logger.debug(f"生成网格信号: {signal.direction.value} "
                            f"{signal.quantity}股 @¥{signal.price:.3f}")

            return signal

        except Exception as e:
            self.logger.error(f"创建网格信号失败: {str(e)}")
            return None

    def _calculate_signal_strength(self, grid_level: GridLevel) -> SignalStrength:
        """计算信号强度"""
        # 基于网格等级偏离中心的距离计算强度
        distance = abs(grid_level.level)

        if distance >= 8:
            return SignalStrength.URGENT
        elif distance >= 5:
            return SignalStrength.STRONG
        elif distance >= 3:
            return SignalStrength.NORMAL
        else:
            return SignalStrength.WEAK

    def _check_rebalance_signal(self, grid_engine: GridEngine, current_price: float,
                               timestamp: datetime) -> Optional[TradingSignal]:
        """检查重新平衡信号"""
        try:
            if not grid_engine.active:
                return None

            # 检查价格偏离程度
            price_deviation = abs(current_price - grid_engine.grid_center) / grid_engine.grid_center
            rebalance_threshold = grid_engine.config.get('rebalance_threshold', 0.15)

            if price_deviation >= rebalance_threshold:
                signal = TradingSignal(
                    symbol=grid_engine.symbol,
                    signal_type=SignalType.REBALANCE,
                    direction=Direction.BUY,  # 重新平衡方向由具体逻辑决定
                    quantity=0,  # 重新平衡信号不涉及具体数量
                    price=current_price,
                    strength=SignalStrength.NORMAL,
                    timestamp=timestamp,
                    source="RebalanceChecker",
                    reason=f"价格偏离 {price_deviation:.2%} 超过阈值 {rebalance_threshold:.2%}",
                    metadata={
                        'price_deviation': price_deviation,
                        'threshold': rebalance_threshold,
                        'current_center': grid_engine.grid_center,
                        'new_center': current_price
                    }
                )

                self.logger.info(f"生成重新平衡信号: 偏离 {price_deviation:.2%}")
                return signal

        except Exception as e:
            self.logger.error(f"检查重新平衡信号失败: {str(e)}")

        return None

    def _check_risk_signals(self, grid_engine: GridEngine, current_price: float,
                           timestamp: datetime) -> List[TradingSignal]:
        """检查风险信号"""
        signals = []

        try:
            if not self.risk_manager:
                return signals

            # 检查止损信号
            stop_loss_signal = self._check_stop_loss_signal(grid_engine, current_price, timestamp)
            if stop_loss_signal:
                signals.append(stop_loss_signal)

            # 检查止盈信号
            take_profit_signal = self._check_take_profit_signal(grid_engine, current_price, timestamp)
            if take_profit_signal:
                signals.append(take_profit_signal)

            # 检查紧急退出信号
            emergency_signal = self._check_emergency_signal(grid_engine, current_price, timestamp)
            if emergency_signal:
                signals.append(emergency_signal)

        except Exception as e:
            self.logger.error(f"检查风险信号失败: {str(e)}")

        return signals

    def _check_stop_loss_signal(self, grid_engine: GridEngine, current_price: float,
                               timestamp: datetime) -> Optional[TradingSignal]:
        """检查止损信号"""
        try:
            performance = grid_engine.calculate_performance()
            total_return = performance['total_return']

            stop_loss_limit = RiskManagerConfig.get_current_limits().stop_loss_pct

            if total_return <= -stop_loss_limit:
                signal = TradingSignal(
                    symbol=grid_engine.symbol,
                    signal_type=SignalType.STOP_LOSS,
                    direction=Direction.SELL,
                    quantity=performance.get('current_position', 0),
                    price=current_price,
                    strength=SignalStrength.URGENT,
                    timestamp=timestamp,
                    source="RiskManager",
                    reason=f"总收益率 {total_return:.2%} 触发止损 {-stop_loss_limit:.2%}",
                    metadata={
                        'current_return': total_return,
                        'stop_loss_limit': stop_loss_limit,
                        'position_size': performance.get('current_position', 0)
                    }
                )

                self.logger.warning(f"生成止损信号: 收益率 {total_return:.2%}")
                return signal

        except Exception as e:
            self.logger.error(f"检查止损信号失败: {str(e)}")

        return None

    def _check_take_profit_signal(self, grid_engine: GridEngine, current_price: float,
                                 timestamp: datetime) -> Optional[TradingSignal]:
        """检查止盈信号"""
        try:
            performance = grid_engine.calculate_performance()
            total_return = performance['total_return']

            take_profit_limit = RiskManagerConfig.get_current_limits().take_profit_pct

            if total_return >= take_profit_limit:
                signal = TradingSignal(
                    symbol=grid_engine.symbol,
                    signal_type=SignalType.TAKE_PROFIT,
                    direction=Direction.SELL,
                    quantity=performance.get('current_position', 0) // 2,  # 止盈一半
                    price=current_price,
                    strength=SignalStrength.STRONG,
                    timestamp=timestamp,
                    source="RiskManager",
                    reason=f"总收益率 {total_return:.2%} 触发止盈 {take_profit_limit:.2%}",
                    metadata={
                        'current_return': total_return,
                        'take_profit_limit': take_profit_limit,
                        'position_size': performance.get('current_position', 0)
                    }
                )

                self.logger.info(f"生成止盈信号: 收益率 {total_return:.2%}")
                return signal

        except Exception as e:
            self.logger.error(f"检查止盈信号失败: {str(e)}")

        return None

    def _check_emergency_signal(self, grid_engine: GridEngine, current_price: float,
                               timestamp: datetime) -> Optional[TradingSignal]:
        """检查紧急退出信号"""
        try:
            # 检查市场异常波动
            market_risk = MarketRiskParams

            # 简化的市场崩溃检测
            if (hasattr(grid_engine, 'previous_price') and
                grid_engine.previous_price > 0):
                price_change = abs(current_price - grid_engine.previous_price) / grid_engine.previous_price

                if price_change >= market_risk.market_crash_threshold:
                    signal = TradingSignal(
                        symbol=grid_engine.symbol,
                        signal_type=SignalType.EMERGENCY_EXIT,
                        direction=Direction.SELL,
                        quantity=grid_engine.calculate_performance().get('current_position', 0),
                        price=current_price,
                        strength=SignalStrength.URGENT,
                        timestamp=timestamp,
                        source="EmergencyChecker",
                        reason=f"价格剧烈波动 {price_change:.2%} 触发紧急退出",
                        metadata={
                            'price_change': price_change,
                            'crash_threshold': market_risk.market_crash_threshold,
                            'previous_price': grid_engine.previous_price,
                            'current_price': current_price
                        }
                    )

                    self.logger.critical(f"生成紧急退出信号: 价格波动 {price_change:.2%}")
                    return signal

        except Exception as e:
            self.logger.error(f"检查紧急信号失败: {str(e)}")

        return None

    def _filter_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """过滤信号"""
        filtered_signals = []

        for signal in signals:
            try:
                # 应用所有过滤器
                valid = True
                for filter_func in self.signal_filters:
                    if not filter_func(signal):
                        valid = False
                        self.logger.debug(f"信号被过滤器拒绝: {filter_func.__name__}")
                        break

                if valid:
                    filtered_signals.append(signal)

            except Exception as e:
                self.logger.error(f"信号过滤异常: {str(e)}")

        return filtered_signals

    def _process_signals(self, signals: List[TradingSignal]):
        """处理信号"""
        for signal in signals:
            try:
                # 记录信号
                self._record_signal(signal)

                # 调用所有处理器
                for handler_func in self.signal_handlers:
                    try:
                        handler_func(signal)
                    except Exception as e:
                        self.logger.error(f"信号处理器异常: {handler_func.__name__}, 错误: {str(e)}")

            except Exception as e:
                self.logger.error(f"信号处理异常: {str(e)}")

    def _record_signal(self, signal: TradingSignal):
        """记录信号"""
        with self._lock:
            self.signal_history.append(signal)

            # 限制历史记录大小
            if len(self.signal_history) > self.max_history_size:
                self.signal_history = self.signal_history[-self.max_history_size:]

            # 更新统计
            self.stats['total_signals'] += 1
            if signal.direction == Direction.BUY:
                self.stats['buy_signals'] += 1
            else:
                self.stats['sell_signals'] += 1

            self.stats['last_signal_time'] = signal.timestamp

    def update_signal_status(self, signal_id: str, status: str, order_id: str = None):
        """更新信号状态"""
        with self._lock:
            for signal in self.signal_history:
                if id(signal) == int(signal_id) or (hasattr(signal, 'signal_id') and signal.signal_id == signal_id):
                    signal.status = status
                    if order_id:
                        signal.order_id = order_id

                    if status in ["EXECUTED", "FILLED"]:
                        self.stats['executed_signals'] += 1
                    elif status in ["REJECTED", "CANCELLED"]:
                        self.stats['rejected_signals'] += 1

                    self.logger.debug(f"信号状态更新: {signal_id} -> {status}")
                    break

    def get_recent_signals(self, symbol: str = None, signal_type: SignalType = None,
                          hours: int = 24) -> List[TradingSignal]:
        """获取最近的信号"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_signals = []

        with self._lock:
            for signal in self.signal_history:
                if signal.timestamp >= cutoff_time:
                    if symbol is None or signal.symbol == symbol:
                        if signal_type is None or signal.signal_type == signal_type:
                            recent_signals.append(signal)

        return sorted(recent_signals, key=lambda x: x.timestamp, reverse=True)

    def get_signal_statistics(self) -> Dict[str, Any]:
        """获取信号统计信息"""
        with self._lock:
            execution_rate = safe_divide(self.stats['executed_signals'], self.stats['total_signals'])

            # 计算不同类型信号的分布
            signal_type_counts = {}
            for signal in self.signal_history:
                signal_type = signal.signal_type.value
                signal_type_counts[signal_type] = signal_type_counts.get(signal_type, 0) + 1

            # 计算成功率（基于执行状态）
            success_rate = safe_divide(
                sum(1 for s in self.signal_history if s.status in ["EXECUTED", "FILLED"]),
                len(self.signal_history)
            ) if self.signal_history else 0

            return {
                'total_signals': self.stats['total_signals'],
                'buy_signals': self.stats['buy_signals'],
                'sell_signals': self.stats['sell_signals'],
                'executed_signals': self.stats['executed_signals'],
                'rejected_signals': self.stats['rejected_signals'],
                'execution_rate': execution_rate,
                'success_rate': success_rate,
                'signal_type_distribution': signal_type_counts,
                'last_signal_time': self.stats['last_signal_time'],
                'active_filters': len(self.signal_filters),
                'active_handlers': len(self.signal_handlers)
            }

    def clear_history(self, hours: int = None):
        """清空信号历史"""
        with self._lock:
            if hours:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                self.signal_history = [s for s in self.signal_history if s.timestamp >= cutoff_time]
                self.logger.info(f"清空 {hours} 小时前的信号历史")
            else:
                self.signal_history.clear()
                self.logger.info("清空所有信号历史")

    def reset_statistics(self):
        """重置统计信息"""
        with self._lock:
            self.stats = {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'executed_signals': 0,
                'rejected_signals': 0,
                'last_signal_time': None
            }
            self.logger.info("信号统计信息已重置")