"""
数据管理器
提供统一的数据获取、缓存和处理接口
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os

from .xtquant_client import XtQuantClient, XtQuantDataError
from config.settings import TradingConfig, DataFrequency
from config.etf_universe import ETFUniverse, ETFInfo
from utils.logger import get_logger
from utils.helpers import retry_on_failure, Timer, safe_divide

class DataCache:
    """数据缓存类"""

    def __init__(self, ttl: int = 300):  # TTL 5分钟
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._lock:
            if key not in self._cache:
                return None

            if time.time() - self._timestamps[key] > self.ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None

            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """设置缓存数据"""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()

    def clear(self, pattern: str = None) -> None:
        """清除缓存"""
        with self._lock:
            if pattern:
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self._cache[k]
                    if k in self._timestamps:
                        del self._timestamps[k]
            else:
                self._cache.clear()
                self._timestamps.clear()

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

class DataManager:
    """数据管理器"""

    def __init__(self, data_dir: str = None, cache_ttl: int = 300):
        """
        初始化数据管理器

        Args:
            data_dir: QMT数据目录
            cache_ttl: 缓存TTL（秒）
        """
        self.data_dir = data_dir or TradingConfig.QMT_DATA_DIR
        self.client = XtQuantClient(data_dir=self.data_dir)
        self.cache = DataCache(ttl=cache_ttl)
        self.logger = get_logger("DataManager")

        # 数据质量统计
        self._stats = {
            'requests': 0,
            'cache_hits': 0,
            'errors': 0,
            'last_update': None
        }

        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=4)

        self.logger.info("数据管理器初始化完成")

    def connect(self) -> bool:
        """连接到数据源"""
        try:
            success = self.client.connect()
            if success:
                self.logger.info("数据管理器连接成功")
                # 预加载一些常用数据
                self._preload_common_data()
            return success
        except Exception as e:
            self.logger.error(f"数据管理器连接失败: {str(e)}")
            return False

    def disconnect(self):
        """断开连接"""
        self.client.disconnect()
        self.executor.shutdown(wait=True)
        self.logger.info("数据管理器已断开连接")

    def _preload_common_data(self):
        """预加载常用数据"""
        try:
            # 预加载默认ETF的最近数据
            default_etfs = ETFUniverse.get_default_selection()
            for etf_code in default_etfs[:2]:  # 只预加载前2个
                self.get_historical_data(etf_code, count=5)
        except Exception as e:
            self.logger.warning(f"预加载数据失败: {str(e)}")

    @retry_on_failure(max_attempts=3, delay=1.0)
    def get_historical_data(self,
                          symbol: str,
                          period: str = '1d',
                          count: int = 100,
                          fields: List[str] = None,
                          start_date: str = None,
                          end_date: str = None,
                          use_cache: bool = True) -> pd.DataFrame:
        """
        获取历史数据

        Args:
            symbol: 股票代码
            period: 数据周期
            count: 数据条数
            fields: 字段列表
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存

        Returns:
            历史数据DataFrame
        """
        self._stats['requests'] += 1

        if fields is None:
            fields = ['open', 'high', 'low', 'close', 'volume']

        # 生成缓存键
        cache_key = f"hist_{symbol}_{period}_{count}_{start_date}_{end_date}{'_'.join(fields)}"

        # 尝试从缓存获取
        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self._stats['cache_hits'] += 1
                self.logger.debug(f"从缓存获取历史数据: {symbol}")
                return cached_data

        try:
            self.logger.debug(f"获取历史数据: {symbol}, 周期: {period}, 条数: {count}")

            # 获取原始数据
            raw_data = self.client.get_local_data(
                stock_list=[symbol],
                field_list=fields,
                period=period,
                start_time=start_date or '',
                end_time=end_date or '',
                count=count
            )

            if not raw_data:
                raise XtQuantDataError(f"未找到数据: {symbol}")

            # 转换为DataFrame
            df = self._format_ohlc_data(raw_data, symbol, fields)

            # 数据质量检查
            df = self._validate_data(df, symbol)

            # 缓存数据
            if use_cache and not df.empty:
                self.cache.set(cache_key, df)

            self._stats['last_update'] = datetime.now()
            return df

        except Exception as e:
            self._stats['errors'] += 1
            error_msg = f"获取历史数据失败: {symbol}, 错误: {str(e)}"
            self.logger.error(error_msg)
            raise XtQuantDataError(error_msg)

    def get_realtime_data(self, symbols: List[str], use_cache: bool = False) -> Dict[str, Dict]:
        """
        获取实时数据

        Args:
            symbols: 股票代码列表
            use_cache: 是否使用缓存

        Returns:
            实时数据字典
        """
        self._stats['requests'] += 1

        try:
            # 对于实时数据，通常不使用缓存或者TTL很短
            if use_cache:
                cache_key = f"realtime_{'_'.join(symbols)}"
                cached_data = self.cache.get(cache_key)
                if cached_data is not None:
                    self._stats['cache_hits'] += 1
                    return cached_data

            self.logger.debug(f"获取实时数据: {symbols}")

            # 获取市场数据
            raw_data = self.client.get_market_data(
                stock_list=symbols,
                period='1d',
                count=1
            )

            # 格式化数据
            result = {}
            for symbol in symbols:
                if symbol in raw_data:
                    result[symbol] = self._format_realtime_data(raw_data[symbol], symbol)

            # 缓存结果（短时间）
            if use_cache and result:
                self.cache.set(cache_key, result)

            return result

        except Exception as e:
            self._stats['errors'] += 1
            error_msg = f"获取实时数据失败: {symbols}, 错误: {str(e)}"
            self.logger.error(error_msg)
            return {}

    def get_batch_historical_data(self,
                                symbols: List[str],
                                period: str = '1d',
                                count: int = 100,
                                fields: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        批量获取历史数据

        Args:
            symbols: 股票代码列表
            period: 数据周期
            count: 数据条数
            fields: 字段列表

        Returns:
            历史数据字典
        """
        self.logger.info(f"批量获取历史数据: {len(symbols)}个标的")

        results = {}
        futures = {}

        # 并发获取数据
        for symbol in symbols:
            future = self.executor.submit(
                self.get_historical_data,
                symbol=symbol,
                period=period,
                count=count,
                fields=fields
            )
            futures[future] = symbol

        # 收集结果
        for future in as_completed(futures, timeout=60):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                self.logger.error(f"获取 {symbol} 数据失败: {str(e)}")
                results[symbol] = pd.DataFrame()

        return results

    def subscribe_realtime(self,
                          symbols: List[str],
                          callback_func: callable,
                          period: str = '1m') -> bool:
        """
        订阅实时数据

        Args:
            symbols: 股票代码列表
            callback_func: 回调函数
            period: 数据周期

        Returns:
            订阅是否成功
        """
        try:
            success_count = 0
            for symbol in symbols:
                if self.client.subscribe_quote(symbol, callback_func, period):
                    success_count += 1

            success_rate = success_count / len(symbols)
            self.logger.info(f"订阅完成: {success_count}/{len(symbols)} 成功")
            return success_rate > 0.5  # 超过一半成功就算成功

        except Exception as e:
            self.logger.error(f"订阅实时数据失败: {str(e)}")
            return False

    def unsubscribe_realtime(self, symbols: List[str]) -> bool:
        """
        取消订阅实时数据

        Args:
            symbols: 股票代码列表

        Returns:
            取消订阅是否成功
        """
        try:
            success_count = 0
            for symbol in symbols:
                if self.client.unsubscribe_quote(symbol):
                    success_count += 1

            self.logger.info(f"取消订阅完成: {success_count}/{len(symbols)} 成功")
            return True

        except Exception as e:
            self.logger.error(f"取消订阅失败: {str(e)}")
            return False

    def get_etf_info(self, symbol: str) -> ETFInfo:
        """
        获取ETF信息

        Args:
            symbol: ETF代码

        Returns:
            ETF信息
        """
        try:
            return ETFUniverse.get_etf_by_code(symbol)
        except ValueError:
            self.logger.warning(f"未找到ETF信息: {symbol}")
            return ETFInfo(symbol, "Unknown ETF", None, "Unknown", 0.0)

    def validate_data_availability(self, symbols: List[str]) -> Dict[str, bool]:
        """
        验证数据可用性

        Args:
            symbols: 股票代码列表

        Returns:
            数据可用性字典
        """
        results = {}
        for symbol in symbols:
            try:
                # 尝试获取最近的数据
                data = self.get_historical_data(symbol, count=1)
                results[symbol] = not data.empty
            except Exception as e:
                self.logger.debug(f"验证 {symbol} 数据可用性失败: {str(e)}")
                results[symbol] = False

        return results

    def _format_ohlc_data(self, raw_data: Dict, symbol: str, fields: List[str]) -> pd.DataFrame:
        """格式化OHLC数据"""
        try:
            # 提取指定字段的数据
            data_list = []
            for field in fields:
                if field in raw_data and symbol in raw_data[field]:
                    field_data = raw_data[field][symbol]
                    if hasattr(field_data, 'index'):
                        df = pd.DataFrame(field_data)
                        if not df.empty:
                            df.columns = [field]
                            data_list.append(df)

            if not data_list:
                return pd.DataFrame()

            # 合并所有字段
            df = data_list[0]
            for field_df in data_list[1:]:
                df = pd.concat([df, field_df], axis=1)

            # 清理数据
            df = df.dropna()
            if not df.empty:
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()

            return df

        except Exception as e:
            self.logger.error(f"格式化OHLC数据失败: {symbol}, 错误: {str(e)}")
            return pd.DataFrame()

    def _format_realtime_data(self, raw_data: Any, symbol: str) -> Dict:
        """格式化实时数据"""
        try:
            # 这里根据XtQuant返回的数据格式进行调整
            if hasattr(raw_data, '__iter__') and not isinstance(raw_data, str):
                data_dict = {}
                for i, field in enumerate(['open', 'high', 'low', 'close', 'volume']):
                    if i < len(raw_data):
                        data_dict[field] = raw_data[i]

                data_dict['symbol'] = symbol
                data_dict['timestamp'] = datetime.now()
                return data_dict
            else:
                return {
                    'symbol': symbol,
                    'price': raw_data,
                    'timestamp': datetime.now()
                }

        except Exception as e:
            self.logger.error(f"格式化实时数据失败: {symbol}, 错误: {str(e)}")
            return {}

    def _validate_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """验证数据质量"""
        if df.empty:
            return df

        # 检查必要的列
        required_columns = ['close']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.logger.warning(f"数据缺少必要列: {missing_columns}, 符号: {symbol}")
            return pd.DataFrame()

        # 检查异常值
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                # 检查负价格
                negative_prices = df[df[col] <= 0]
                if not negative_prices.empty:
                    self.logger.warning(f"发现负价格数据: {symbol}, 列: {col}, 数量: {len(negative_prices)}")

                # 检查极端变化
                if len(df) > 1:
                    price_change = df[col].pct_change().abs()
                    extreme_changes = df[price_change > 0.2]  # 20%以上的变化
                    if not extreme_changes.empty:
                        self.logger.warning(f"发现极端价格变化: {symbol}, 列: {col}, 数量: {len(extreme_changes)}")

        # 检查成交量
        if 'volume' in df.columns:
            negative_volume = df[df['volume'] < 0]
            if not negative_volume.empty:
                self.logger.warning(f"发现负成交量数据: {symbol}, 数量: {len(negative_volume)}")

        return df

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据管理器统计信息"""
        cache_hit_rate = safe_divide(self._stats['cache_hits'], self._stats['requests'])
        error_rate = safe_divide(self._stats['errors'], self._stats['requests'])

        return {
            'total_requests': self._stats['requests'],
            'cache_hits': self._stats['cache_hits'],
            'cache_hit_rate': cache_hit_rate,
            'errors': self._stats['errors'],
            'error_rate': error_rate,
            'cache_size': self.cache.size(),
            'last_update': self._stats['last_update'],
            'connected': self.client.is_connected
        }

    def clear_cache(self, symbol: str = None):
        """清除缓存"""
        if symbol:
            self.cache.clear(symbol)
            self.logger.info(f"清除 {symbol} 的缓存")
        else:
            self.cache.clear()
            self.logger.info("清除所有缓存")

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()