"""
XtQuant客户端封装
提供与QMT/XtQuant系统的连接和数据获取功能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

try:
    from xtquant import xtdata, xttrader
    XTQUANT_AVAILABLE = True
except ImportError:
    print("警告: XtQuant库未安装或未正确配置")
    XTQUANT_AVAILABLE = False

from config.settings import TradingConfig, DataFrequency
from utils.logger import get_logger
from utils.helpers import retry_on_failure, Timer
from utils.xtquant_wrapper import get_xtquant_wrapper

class XtQuantConnectionError(Exception):
    """XtQuant连接异常"""
    pass

class XtQuantDataError(Exception):
    """XtQuant数据异常"""
    pass

class XtQuantClient:
    """XtQuant客户端封装类"""

    def __init__(self, data_dir: str = None, session_id: int = 0):
        """
        初始化XtQuant客户端

        Args:
            data_dir: QMT数据目录路径
            session_id: 会话ID
        """
        self.data_dir = data_dir or TradingConfig.QMT_DATA_DIR
        self.session_id = session_id
        self.logger = get_logger("XtQuantClient")

        # 初始化API包装器（包含回退机制）
        self.api_wrapper = get_xtquant_wrapper(self.data_dir, self.session_id)

        self._subscribed_symbols = set()
        self._data_callbacks = {}
        self._lock = threading.Lock()

        # 连接状态监控
        self._last_ping_time = None
        self._connection_check_interval = 30  # 秒

    def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        连接到QMT系统（现在支持自动回退）

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            连接是否成功（如果使用回退系统也返回True）
        """
        # 检查API包装器状态
        connection_status = self.api_wrapper.get_connection_status()

        if connection_status['xtquant_available'] and connection_status['is_connected']:
            self.logger.info("XtQuant连接成功")
            return True
        elif connection_status['fallback_system']:
            self.logger.info("XtQuant不可用，使用回退系统")
            return True
        else:
            # 尝试重新连接
            self.logger.info("尝试重新连接XtQuant...")
            return self.api_wrapper.reconnect()

    def disconnect(self):
        """断开连接"""
        with self._lock:
            # 取消所有订阅
            for symbol in list(self._subscribed_symbols):
                self.unsubscribe_quote(symbol)

            self._connected = False
            self.logger.info("XtQuant连接已断开")

    @property
    def is_connected(self) -> bool:
        """检查连接状态（现在包括回退系统）"""
        # 检查API包装器状态
        connection_status = self.api_wrapper.get_connection_status()

        # 如果XtQuant连接正常或者回退系统激活，都认为"已连接"
        return (connection_status['xtquant_available'] and connection_status['is_connected']) or connection_status['fallback_system']

    def _ping_connection(self) -> bool:
        """检查连接是否正常"""
        # 尝试获取测试数据来检查连接
        try:
            test_data = self.api_wrapper.get_market_data(
                stock_list=["000001.SZ"],
                period='1d',
                count=1
            )

            if test_data:
                self._last_ping_time = datetime.now()
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"连接检查失败: {str(e)}")
            return False

    def get_local_data(self,
                      stock_list: List[str],
                      field_list: List[str] = None,
                      period: str = '1d',
                      start_time: str = '',
                      end_time: str = '',
                      count: int = -1,
                      dividend_type: str = 'none') -> Dict[str, Any]:
        """
        获取本地历史数据，使用robust wrapper自动回退

        Args:
            stock_list: 股票代码列表
            field_list: 字段列表，如['open', 'high', 'low', 'close', 'volume']
            period: 数据周期
            start_time: 开始时间
            end_time: 结束时间
            count: 数据条数
            dividend_type: 复权类型

        Returns:
            数据字典，包含自动回退数据
        """
        self.logger.debug(f"获取本地数据: {stock_list}, 字段: {field_list}, 周期: {period}")

        try:
            # 使用robust wrapper而不是直接调用xtdata
            data = self.api_wrapper.get_local_data(
                stock_list=stock_list,
                field_list=field_list,
                period=period,
                start_time=start_time,
                end_time=end_time,
                count=count,
                dividend_type=dividend_type,
                data_dir=self.data_dir
            )

            if data is None or len(data) == 0:
                self.logger.warning(f"未找到本地数据: {stock_list}")
                return {}

            # 记录是否使用了回退系统
            connection_status = self.api_wrapper.get_connection_status()
            if connection_status['fallback_system']:
                self.logger.info(f"使用回退数据获取本地数据: {stock_list}")

            return data

        except Exception as e:
            error_msg = f"获取本地数据失败: {str(e)}"
            self.logger.error(error_msg)
            raise XtQuantDataError(error_msg)

    def get_market_data(self,
                       stock_list: List[str],
                       period: str = '1d',
                       count: int = 1,
                       dividend_type: str = 'none',
                       fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取市场数据（现在支持自动回退）

        Args:
            stock_list: 股票代码列表
            period: 数据周期
            count: 数据条数
            dividend_type: 复权类型
            fields: 需要的字段列表

        Returns:
            市场数据字典
        """
        self.logger.debug(f"获取市场数据: {stock_list}, 周期: {period}, 条数: {count}")

        try:
            # 使用API包装器获取数据（自动处理回退）
            data = self.api_wrapper.get_market_data(
                stock_list=stock_list,
                period=period,
                count=count,
                dividend_type=dividend_type,
                fields=fields,
                data_dir=self.data_dir
            )

            if data is None or len(data) == 0:
                raise XtQuantDataError(f"未找到市场数据: {stock_list}")

            # 记录是否使用了回退系统
            connection_status = self.api_wrapper.get_connection_status()
            if connection_status['fallback_system']:
                self.logger.info(f"使用回退数据获取市场数据: {stock_list}")

            return data

        except Exception as e:
            error_msg = f"获取市场数据失败: {str(e)}"
            self.logger.error(error_msg)
            raise XtQuantDataError(error_msg)

    def subscribe_quote(self, symbol: str, callback=None, period: str = '1m') -> bool:
        """
        订阅实时行情

        Args:
            symbol: 股票代码
            callback: 回调函数
            period: 数据周期

        Returns:
            订阅是否成功
        """
        if not self.is_connected:
            raise XtQuantConnectionError("未连接到XtQuant系统")

        with self._lock:
            if symbol in self._subscribed_symbols:
                self.logger.debug(f"已订阅: {symbol}")
                return True

            try:
                if callback:
                    self._data_callbacks[symbol] = callback

                xtdata.subscribe_quote(
                    stock_code=symbol,
                    period=period,
                    count=-1,
                    callback=self._default_callback if callback is None else callback
                )

                self._subscribed_symbols.add(symbol)
                self.logger.info(f"订阅成功: {symbol} ({period})")
                return True

            except Exception as e:
                error_msg = f"订阅失败: {symbol}, 错误: {str(e)}"
                self.logger.error(error_msg)
                return False

    def unsubscribe_quote(self, symbol: str) -> bool:
        """
        取消订阅实时行情

        Args:
            symbol: 股票代码

        Returns:
            取消订阅是否成功
        """
        with self._lock:
            if symbol not in self._subscribed_symbols:
                self.logger.debug(f"未订阅: {symbol}")
                return True

            try:
                xtdata.subscribe_quote(stock_code=symbol, period='1m', count=0)

                if symbol in self._data_callbacks:
                    del self._data_callbacks[symbol]

                self._subscribed_symbols.remove(symbol)
                self.logger.info(f"取消订阅成功: {symbol}")
                return True

            except Exception as e:
                error_msg = f"取消订阅失败: {symbol}, 错误: {str(e)}"
                self.logger.error(error_msg)
                return False

    def _default_callback(self, data):
        """默认数据回调函数"""
        try:
            if isinstance(data, dict):
                symbol = data.get('symbol', 'Unknown')
                timestamp = data.get('time', datetime.now())
                price = data.get('price', 0)
                volume = data.get('volume', 0)

                self.logger.debug(f"实时数据: {symbol} 价格:{price} 成交量:{volume} 时间:{timestamp}")

                # 调用特定符号的回调
                if symbol in self._data_callbacks:
                    self._data_callbacks[symbol](data)

        except Exception as e:
            self.logger.error(f"数据处理回调异常: {str(e)}")

    def get_full_tick(self, stock_list: List[str]) -> Dict[str, Any]:
        """
        获取完整tick数据

        Args:
            stock_list: 股票代码列表

        Returns:
            tick数据字典
        """
        try:
            return xtdata.get_full_tick(stock_list)
        except Exception as e:
            error_msg = f"获取tick数据失败: {str(e)}"
            self.logger.error(error_msg)
            raise XtQuantDataError(error_msg)

    def run_quote_loop(self):
        """运行行情循环"""
        if not self.is_connected:
            raise XtQuantConnectionError("未连接到XtQuant系统")

        try:
            self.logger.info("启动行情循环")
            xtdata.run()
        except KeyboardInterrupt:
            self.logger.info("行情循环被用户中断")
        except Exception as e:
            self.logger.error(f"行情循环异常: {str(e)}")
            raise

    def get_current_price(self, symbol: str) -> float:
        """
        获取单个证券的当前价格（支持回退）

        Args:
            symbol: 证券代码

        Returns:
            当前价格
        """
        try:
            return self.api_wrapper.get_single_price(symbol)
        except Exception as e:
            self.logger.error(f"获取{symbol}价格失败: {str(e)}")
            return 0.0

    def get_trading_calendar(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日历

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易日列表
        """
        try:
            # 如果XtQuant可用，使用原始方法
            if XTQUANT_AVAILABLE and self.api_wrapper.xtdata:
                return xtdata.get_trading_date(start_date, end_date)
            else:
                # 生成模拟交易日历
                self.logger.warning("XtQuant不可用，生成模拟交易日历")
                return self._generate_trading_calendar(start_date, end_date)
        except Exception as e:
            self.logger.error(f"获取交易日历失败: {str(e)}")
            return []

    def _generate_trading_calendar(self, start_date: str, end_date: str) -> List[str]:
        """生成模拟交易日历"""
        from datetime import datetime, timedelta
        import numpy as np

        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")

        trading_days = []
        current_dt = start_dt

        while current_dt <= end_dt:
            # 排除周末
            if current_dt.weekday() < 5:  # 0-4是周一到周五
                # 随机排除一些节假日（约5%的概率）
                if np.random.random() > 0.05:
                    trading_days.append(current_dt.strftime("%Y%m%d"))
            current_dt += timedelta(days=1)

        return trading_days

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def __del__(self):
        """析构函数"""
        try:
            self.disconnect()
        except:
            pass