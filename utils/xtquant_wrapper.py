# -*- coding: utf-8 -*-
"""
XtQuant API 包装器
提供统一的API接口，自动处理参数映射和回退机制
"""

import sys
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger
from utils.data_fallback import fallback_system

class XtQuantAPIWrapper:
    """XtQuant API 包装器"""

    def __init__(self, data_dir: Optional[str] = None, session_id: Optional[int] = None):
        self.logger = get_logger("XtQuantAPIWrapper")
        self.data_dir = data_dir
        self.session_id = session_id
        self.xtdata = None
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.circuit_breaker_timeout = 300  # 5分钟熔断时间
        self.last_failure_time = None
        self.is_connected = False

        # 尝试初始化XtQuant
        self._initialize_xtquant()

    def _initialize_xtquant(self):
        """初始化XtQuant连接"""
        try:
            import xtquant.xtdata as xtdata
            self.xtdata = xtdata
            self.logger.info("XtQuant库导入成功")

            # 测试连接
            if self._test_connection():
                self.is_connected = True
                self.logger.info("XtQuant连接测试成功")
            else:
                self.logger.warning("XtQuant连接测试失败，将使用回退系统")

        except ImportError as e:
            self.logger.warning(f"XtQuant库导入失败: {e}")
            self.xtdata = None
        except Exception as e:
            self.logger.warning(f"XtQuant初始化失败: {e}")
            self.xtdata = None

    def _test_connection(self) -> bool:
        """测试XtQuant连接"""
        if not self.xtdata:
            return False

        try:
            # 尝试获取一些基本数据来测试连接
            # 这里使用最简单的参数组合
            result = self.xtdata.get_market_data(
                stock_list=["000001.SZ"],
                period='1d',
                count=1
            )
            return result is not None
        except Exception as e:
            self.logger.debug(f"XtQuant连接测试失败: {e}")
            return False

    def _is_circuit_breaker_active(self) -> bool:
        """检查熔断器是否激活"""
        if self.last_failure_time is None:
            return False

        elapsed = time.time() - self.last_failure_time
        return elapsed < self.circuit_breaker_timeout

    def get_market_data(self,
                       symbols: Optional[List[str]] = None,
                       stock_list: Optional[List[str]] = None,
                       period: str = '1d',
                       count: int = 1,
                       fields: Optional[List[str]] = None,
                       dividend_type: str = 'none',
                       fill_data: bool = True,
                       data_dir: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        获取市场数据，支持参数映射和自动回退

        Args:
            symbols: ETF代码列表（新参数名）
            stock_list: ETF代码列表（旧参数名）
            period: 数据周期
            count: 数据条数
            fields: 需要的字段列表
            dividend_type: 除息类型
            fill_data: 是否填充数据
            data_dir: 数据目录
            **kwargs: 其他参数

        Returns:
            市场数据字典
        """
        # 统一处理symbols和stock_list参数
        target_symbols = symbols or stock_list
        if not target_symbols:
            self.logger.warning("未提供symbols或stock_list参数")
            return {}

        # 检查熔断器状态
        if self._is_circuit_breaker_active():
            self.logger.info("熔断器激活，使用回退数据")
            return self._get_fallback_data(target_symbols, period, count, fields)

        # 如果XtQuant不可用，直接使用回退数据
        if not self.xtdata or not self.is_connected:
            return self._get_fallback_data(target_symbols, period, count, fields)

        # 尝试使用XtQuant获取数据
        try:
            # 尝试不同的参数组合
            result = self._try_xtquant_calls(target_symbols, period, count, fields, dividend_type, fill_data)

            if result:
                self.connection_attempts = 0  # 重置失败计数
                return result
            else:
                raise Exception("XtQuant返回空数据")

        except Exception as e:
            self.logger.warning(f"XtQuant数据获取失败: {e}")
            self._handle_failure()
            return self._get_fallback_data(target_symbols, period, count, fields)

    def _try_xtquant_calls(self,
                          symbols: List[str],
                          period: str,
                          count: int,
                          fields: Optional[List[str]],
                          dividend_type: str,
                          fill_data: bool) -> Optional[Dict[str, Any]]:
        """尝试不同的XtQuant API调用方式"""

        attempts = [
            # 尝试1: 使用stock_list参数（原代码中的用法）
            {
                'params': {
                    'stock_list': symbols,
                    'period': period,
                    'count': count,
                    'dividend_type': dividend_type,
                    'fill_data': fill_data
                },
                'description': 'stock_list参数'
            },

            # 尝试2: 使用symbols参数（如果支持的话）
            {
                'params': {
                    'symbols': symbols,
                    'period': period,
                    'count': count,
                    'dividend_type': dividend_type,
                    'fill_data': fill_data
                },
                'description': 'symbols参数'
            },

            # 尝试3: 最小参数集
            {
                'params': {
                    'stock_list': symbols,
                    'period': period,
                    'count': count
                },
                'description': '最小参数集'
            },

            # 尝试4: 带data_dir参数（如果支持的话）
            {
                'params': {
                    'stock_list': symbols,
                    'period': period,
                    'count': count,
                    'data_dir': self.data_dir or data_dir
                },
                'description': '带data_dir参数'
            }
        ]

        for attempt in attempts:
            try:
                self.logger.debug(f"尝试XtQuant调用: {attempt['description']}")
                result = self.xtdata.get_market_data(**attempt['params'])

                if result is not None:
                    self.logger.debug(f"XtQuant调用成功: {attempt['description']}")
                    return result

            except Exception as e:
                self.logger.debug(f"XtQuant调用失败 ({attempt['description']}): {e}")
                continue

        return None

    def _get_fallback_data(self,
                          symbols: List[str],
                          period: str,
                          count: int,
                          fields: Optional[List[str]]) -> Dict[str, Any]:
        """获取回退数据"""
        return fallback_system.get_simulated_market_data(
            symbols=symbols,
            period=period,
            count=count,
            fields=fields
        )

    def _handle_failure(self):
        """处理失败情况"""
        self.connection_attempts += 1
        self.last_failure_time = time.time()

        if self.connection_attempts >= self.max_connection_attempts:
            self.logger.warning(f"连续{self.max_connection_attempts}次连接失败，激活熔断器")
            self.is_connected = False

    def reconnect(self) -> bool:
        """尝试重新连接"""
        self.logger.info("尝试重新连接XtQuant...")
        self.connection_attempts = 0
        self.last_failure_time = None

        # 重新初始化
        self._initialize_xtquant()
        return self.is_connected

    def get_single_price(self, symbol: str) -> float:
        """获取单个ETF的最新价格"""
        # 检查熔断器
        if self._is_circuit_breaker_active():
            return fallback_system.get_simulated_price(symbol)

        # 尝试XtQuant
        if self.xtdata and self.is_connected:
            try:
                data = self.get_market_data(stock_list=[symbol], count=1)
                if data and symbol in data:
                    # 尝试获取收盘价
                    market_data = data[symbol]
                    if hasattr(market_data, 'close'):
                        return float(market_data.close)
                    elif isinstance(market_data, dict) and 'close' in market_data:
                        return float(market_data['close'])

            except Exception as e:
                self.logger.warning(f"获取{symbol}价格失败: {e}")
                self._handle_failure()

        # 回退到模拟价格
        return fallback_system.get_simulated_price(symbol)

    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            'xtquant_available': self.xtdata is not None,
            'is_connected': self.is_connected,
            'connection_attempts': self.connection_attempts,
            'circuit_breaker_active': self._is_circuit_breaker_active(),
            'fallback_system': fallback_system.is_fallback_active(),
            'last_failure_time': self.last_failure_time
        }

# 全局包装器实例
_global_wrapper = None

def get_xtquant_wrapper(data_dir: Optional[str] = None, session_id: Optional[int] = None) -> XtQuantAPIWrapper:
    """获取全局XtQuant包装器实例"""
    global _global_wrapper
    if _global_wrapper is None:
        _global_wrapper = XtQuantAPIWrapper(data_dir, session_id)
    return _global_wrapper