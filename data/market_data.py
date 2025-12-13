"""
实时数据处理器
处理实时行情数据，计算技术指标和生成交易信号
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
import threading
import time
from collections import deque, defaultdict

from .data_manager import DataManager
from config.settings import TradingConfig
from utils.logger import get_logger
from utils.helpers import calculate_returns, calculate_volatility

class MarketDataProcessor:
    """实时数据处理器"""

    def __init__(self, data_manager: DataManager, window_size: int = 100):
        """
        初始化数据处理器

        Args:
            data_manager: 数据管理器实例
            window_size: 数据窗口大小
        """
        self.data_manager = data_manager
        self.window_size = window_size
        self.logger = get_logger("MarketDataProcessor")

        # 实时数据缓存
        self._price_buffers = defaultdict(lambda: deque(maxlen=window_size))
        self._volume_buffers = defaultdict(lambda: deque(maxlen=window_size))
        self._last_prices = {}
        self._last_updates = {}

        # 技术指标缓存
        self._indicators = defaultdict(dict)

        # 回调函数注册
        self._callbacks = {
            'price_update': [],
            'indicator_update': [],
            'signal_generated': []
        }

        # 处理状态
        self._running = False
        self._processing_thread = None
        self._lock = threading.RLock()

        self.logger.info("实时数据处理器初始化完成")

    def start_processing(self):
        """启动数据处理"""
        if self._running:
            return

        self._running = True
        self._processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._processing_thread.start()

        self.logger.info("实时数据处理已启动")

    def stop_processing(self):
        """停止数据处理"""
        if not self._running:
            return

        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=5)

        self.logger.info("实时数据处理已停止")

    def add_symbol(self, symbol: str):
        """
        添加处理标的

        Args:
            symbol: 股票代码
        """
        with self._lock:
            if symbol not in self._price_buffers:
                self._price_buffers[symbol] = deque(maxlen=self.window_size)
                self._volume_buffers[symbol] = deque(maxlen=self.window_size)

                # 尝试加载历史数据
                try:
                    hist_data = self.data_manager.get_historical_data(
                        symbol, count=self.window_size
                    )
                    if not hist_data.empty:
                        for idx, row in hist_data.iterrows():
                            self._price_buffers[symbol].append(row['close'])
                            if 'volume' in row:
                                self._volume_buffers[symbol].append(row['volume'])

                        self._last_prices[symbol] = hist_data.iloc[-1]['close']
                        self._last_updates[symbol] = datetime.now()

                        self.logger.debug(f"加载 {symbol} 历史数据: {len(hist_data)} 条")
                except Exception as e:
                    self.logger.warning(f"加载 {symbol} 历史数据失败: {str(e)}")

    def remove_symbol(self, symbol: str):
        """
        移除处理标的

        Args:
            symbol: 股票代码
        """
        with self._lock:
            self._price_buffers.pop(symbol, None)
            self._volume_buffers.pop(symbol, None)
            self._last_prices.pop(symbol, None)
            self._last_updates.pop(symbol, None)
            self._indicators.pop(symbol, None)

    def update_price(self, symbol: str, price: float, volume: int = 0, timestamp: datetime = None):
        """
        更新价格数据

        Args:
            symbol: 股票代码
            price: 价格
            volume: 成交量
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = datetime.now()

        with self._lock:
            # 更新价格缓存
            self._price_buffers[symbol].append(price)
            self._volume_buffers[symbol].append(volume)
            self._last_prices[symbol] = price
            self._last_updates[symbol] = timestamp

            # 触发价格更新回调
            self._trigger_callbacks('price_update', {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'timestamp': timestamp,
                'change': self._calculate_price_change(symbol, price)
            })

            # 计算技术指标
            indicators = self._calculate_indicators(symbol)
            if indicators:
                self._indicators[symbol].update(indicators)

                # 触发指标更新回调
                self._trigger_callbacks('indicator_update', {
                    'symbol': symbol,
                    'indicators': indicators,
                    'timestamp': timestamp
                })

    def _calculate_price_change(self, symbol: str, current_price: float) -> Dict[str, float]:
        """计算价格变化"""
        if symbol not in self._price_buffers or len(self._price_buffers[symbol]) < 2:
            return {'change': 0.0, 'change_pct': 0.0}

        previous_price = list(self._price_buffers[symbol])[-2]
        change = current_price - previous_price
        change_pct = safe_divide(change, previous_price) if previous_price > 0 else 0.0

        return {
            'change': change,
            'change_pct': change_pct
        }

    def _calculate_indicators(self, symbol: str) -> Dict[str, float]:
        """计算技术指标"""
        if symbol not in self._price_buffers or len(self._price_buffers[symbol]) < 10:
            return {}

        prices = list(self._price_buffers[symbol])
        volumes = list(self._volume_buffers[symbol]) if symbol in self._volume_buffers else []

        indicators = {}

        try:
            # 基础统计指标
            indicators['current_price'] = prices[-1]
            indicators['sma_5'] = np.mean(prices[-5:])
            indicators['sma_10'] = np.mean(prices[-10:])
            indicators['sma_20'] = np.mean(prices[-20:]) if len(prices) >= 20 else np.mean(prices)
            indicators['ema_12'] = self._calculate_ema(prices, 12)
            indicators['ema_26'] = self._calculate_ema(prices, 26)

            # 波动率指标
            if len(prices) >= 20:
                price_series = pd.Series(prices)
                returns = price_series.pct_change().dropna()
                indicators['volatility_20'] = returns.std() * np.sqrt(252)  # 年化波动率
                indicators['atr_14'] = self._calculate_atr(prices, volumes, 14)

            # 动量指标
            if len(prices) >= 14:
                indicators['rsi_14'] = self._calculate_rsi(prices, 14)
                indicators['momentum_10'] = (prices[-1] / prices[-10] - 1) if len(prices) >= 10 else 0

            # MACD指标
            if len(prices) >= 26:
                ema_12 = self._calculate_ema(prices, 12)
                ema_26 = self._calculate_ema(prices, 26)
                indicators['macd'] = ema_12 - ema_26
                indicators['macd_signal'] = self._calculate_ema(
                    [indicators['macd']] * min(len(prices), 9), 9
                )
                indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']

            # 布林带
            if len(prices) >= 20:
                sma_20 = indicators['sma_20']
                std_20 = np.std(prices[-20:])
                indicators['bb_upper'] = sma_20 + 2 * std_20
                indicators['bb_lower'] = sma_20 - 2 * std_20
                indicators['bb_width'] = indicators['bb_upper'] - indicators['bb_lower']
                indicators['bb_position'] = (prices[-1] - indicators['bb_lower']) / indicators['bb_width']

            # 成交量指标
            if volumes:
                indicators['volume_sma_10'] = np.mean(volumes[-10:]) if len(volumes) >= 10 else np.mean(volumes)
                indicators['volume_ratio'] = volumes[-1] / indicators['volume_sma_10'] if indicators['volume_sma_10'] > 0 else 1.0

        except Exception as e:
            self.logger.error(f"计算技术指标失败: {symbol}, 错误: {str(e)}")

        return indicators

    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """计算EMA"""
        if not prices or period <= 0:
            return 0.0

        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_atr(self, prices: List[float], volumes: List[int], period: int = 14) -> float:
        """计算ATR（平均真实范围）"""
        if len(prices) < period + 1:
            return 0.0

        tr_values = []
        for i in range(1, len(prices)):
            high_low = prices[i] - prices[i-1]
            high_close = abs(prices[i] - prices[i-1])
            low_close = abs(prices[i-1] - prices[i])

            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)

        if not tr_values:
            return 0.0

        return np.mean(tr_values[-period:])

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        return self._last_prices.get(symbol)

    def get_price_history(self, symbol: str, count: int = None) -> List[float]:
        """获取价格历史"""
        if symbol not in self._price_buffers:
            return []

        prices = list(self._price_buffers[symbol])
        if count:
            return prices[-count:]
        return prices

    def get_indicators(self, symbol: str) -> Dict[str, float]:
        """获取技术指标"""
        return self._indicators.get(symbol, {})

    def register_callback(self, event_type: str, callback: Callable):
        """
        注册回调函数

        Args:
            event_type: 事件类型 ('price_update', 'indicator_update', 'signal_generated')
            callback: 回调函数
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            self.logger.debug(f"注册 {event_type} 回调函数")
        else:
            self.logger.warning(f"未知的事件类型: {event_type}")

    def _trigger_callbacks(self, event_type: str, data: Dict[str, Any]):
        """触发回调函数"""
        for callback in self._callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"回调函数执行失败: {event_type}, 错误: {str(e)}")

    def _processing_loop(self):
        """数据处理循环"""
        self.logger.info("数据处理循环已启动")

        while self._running:
            try:
                # 定期检查数据质量
                self._check_data_quality()

                # 清理过期数据
                self._cleanup_expired_data()

                time.sleep(10)  # 每10秒执行一次

            except Exception as e:
                self.logger.error(f"数据处理循环异常: {str(e)}")
                time.sleep(5)

    def _check_data_quality(self):
        """检查数据质量"""
        current_time = datetime.now()

        for symbol in list(self._last_updates.keys()):
            last_update = self._last_updates[symbol]
            if (current_time - last_update).seconds > 300:  # 5分钟没有更新
                self.logger.warning(f"数据过期: {symbol}, 最后更新: {last_update}")

    def _cleanup_expired_data(self):
        """清理过期数据"""
        current_time = datetime.now()
        expired_symbols = []

        for symbol, last_update in self._last_updates.items():
            if (current_time - last_update).seconds > 1800:  # 30分钟没有数据
                expired_symbols.append(symbol)

        for symbol in expired_symbols:
            self.remove_symbol(symbol)
            self.logger.info(f"清理过期数据: {symbol}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取处理器统计信息"""
        with self._lock:
            return {
                'processing_symbols': len(self._price_buffers),
                'total_callbacks': {
                    event_type: len(callbacks)
                    for event_type, callbacks in self._callbacks.items()
                },
                'last_updates': dict(self._last_updates),
                'running': self._running
            }

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法"""
    if denominator == 0:
        return default
    return numerator / denominator