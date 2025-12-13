"""
辅助工具函数
提供各种通用的辅助功能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import time
import json
import os

def format_currency(amount: float, currency: str = "¥") -> str:
    """格式化货币显示"""
    return f"{currency}{amount:,.2f}"

def format_percentage(pct: float, decimal_places: int = 2) -> str:
    """格式化百分比显示"""
    return f"{pct * 100:.{decimal_places}f}%"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，避免除零错误"""
    if denominator == 0:
        return default
    return numerator / denominator

def calculate_returns(prices: pd.Series) -> pd.Series:
    """计算收益率序列"""
    return prices.pct_change().fillna(0)

def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    """计算累计收益率"""
    return (1 + returns).cumprod() - 1

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """计算夏普比率"""
    excess_returns = returns - risk_free_rate / 252  # 假设252个交易日
    if excess_returns.std() == 0:
        return 0.0
    return excess_returns.mean() / excess_returns.std() * np.sqrt(252)

def calculate_max_drawdown(prices: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
    """计算最大回撤及其时间点"""
    peak = prices.expanding().max()
    drawdown = (prices - peak) / peak
    max_dd = drawdown.min()

    if max_dd == 0:
        return 0.0, None, None

    end_date = drawdown.idxmin()
    start_date = prices[:end_date].idxmax()

    return max_dd, start_date, end_date

def calculate_volatility(returns: pd.Series, annualize: bool = True) -> float:
    """计算波动率"""
    vol = returns.std()
    if annualize:
        vol *= np.sqrt(252)
    return vol

def validate_trading_symbol(symbol: str) -> bool:
    """验证交易符号格式"""
    if not symbol or not isinstance(symbol, str):
        return False

    # 检查格式：6位数字.交易所代码
    parts = symbol.split('.')
    if len(parts) != 2:
        return False

    if len(parts[0]) != 6 or not parts[0].isdigit():
        return False

    if parts[1] not in ['SZ', 'SH', 'BJ']:
        return False

    return True

def parse_time_string(time_str: str) -> datetime:
    """解析时间字符串"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"无法解析时间字符串: {time_str}")

def is_trading_time(dt: datetime = None) -> bool:
    """检查是否为交易时间"""
    if dt is None:
        dt = datetime.now()

    # 检查是否为工作日
    if dt.weekday() >= 5:  # 周六、周日
        return False

    # 检查时间
    current_time = dt.time()

    # 上午交易时间 9:30-11:30
    morning_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
    morning_end = datetime.strptime("11:30:00", "%H:%M:%S").time()

    # 下午交易时间 13:00-15:00
    afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
    afternoon_end = datetime.strptime("15:00:00", "%H:%M:%S").time()

    return (morning_start <= current_time <= morning_end or
            afternoon_start <= current_time <= afternoon_end)

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # 指数退避

            raise last_exception
        return wrapper
    return decorator

def save_to_json(data: Any, file_path: str, indent: int = 2):
    """保存数据到JSON文件"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=str)

def load_from_json(file_path: str) -> Any:
    """从JSON文件加载数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def round_to_nearest(price: float, tick_size: float = 0.001) -> float:
    """四舍五入到最小价格变动单位"""
    return round(price / tick_size) * tick_size

def calculate_position_size(capital: float, price: float,
                          position_pct: float, min_unit: int = 100) -> int:
    """计算持仓数量"""
    target_amount = capital * position_pct
    shares = int(target_amount / price)

    # 调整到最小交易单位的整数倍
    shares = (shares // min_unit) * min_unit

    return max(shares, min_unit) if shares >= min_unit else 0

def normalize_symbol(symbol: str) -> str:
    """标准化交易符号"""
    symbol = symbol.upper().strip()

    # 添加交易所后缀（如果没有）
    if '.' not in symbol:
        # 根据代码判断交易所
        if symbol.startswith('00') or symbol.startswith('30'):
            symbol += '.SZ'  # 深交所
        elif symbol.startswith('6'):
            symbol += '.SH'  # 上交所
        elif symbol.startswith('8'):
            symbol += '.BJ'  # 北交所

    return symbol

def batch_process(data: List[Any], batch_size: int, process_func):
    """批量处理数据"""
    results = []

    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_result = process_func(batch)
        results.extend(batch_result if isinstance(batch_result, list) else [batch_result])

    return results

def memory_usage() -> float:
    """获取当前内存使用量（MB）"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0

def benchmark_function(func, *args, **kwargs):
    """函数性能基准测试"""
    start_time = time.time()
    start_memory = memory_usage()

    try:
        result = func(*args, **kwargs)
        end_time = time.time()
        end_memory = memory_usage()

        return {
            'result': result,
            'execution_time': end_time - start_time,
            'memory_used': end_memory - start_memory
        }
    except Exception as e:
        end_time = time.time()
        end_memory = memory_usage()

        return {
            'error': str(e),
            'execution_time': end_time - start_time,
            'memory_used': end_memory - start_memory
        }

class Timer:
    """简单的计时器上下文管理器"""

    def __init__(self, description: str = ""):
        self.description = description
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time

        if self.description:
            print(f"{self.description}: {elapsed:.3f}秒")
        else:
            print(f"执行时间: {elapsed:.3f}秒")

    @property
    def elapsed_time(self) -> float:
        """获取已用时间"""
        if self.start_time is None:
            return 0.0

        end = self.end_time if self.end_time else time.time()
        return end - self.start_time