"""
基于XtQuant的ETF网格交易策略配置文件
包含策略参数、风险参数、ETF标的池等配置信息
"""

import os
from datetime import datetime, time
from typing import Dict, Any, List, Optional

class TradingConfig:
    """交易配置类"""

    # XtQuant数据路径
    QMT_DATA_DIR = r"C:\Users\zhanghang\国金证券QMT交易端\datadir"

    # 交易时间设置
    TRADING_START_TIME = time(9, 30)  # 开盘时间
    TRADING_END_TIME = time(15, 0)    # 收盘时间
    LUNCH_BREAK_START = time(11, 30)  # 午休开始
    LUNCH_BREAK_END = time(13, 0)     # 午休结束

    # 系统运行参数
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/etf_grid_trading.log"
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # 数据获取参数
    DATA_RETRY_COUNT = 3
    DATA_RETRY_DELAY = 1  # 秒
    REALTIME_UPDATE_INTERVAL = 1  # 秒

    # 网格策略默认参数
    DEFAULT_GRID_LEVELS = 20  # 总网格数
    DEFAULT_GRID_SPACING_PCT = 0.02  # 默认网格间距百分比
    DEFAULT_REFERENCE_PERIOD = 20  # 基准价格计算周期
    DEFAULT_REBALANCE_THRESHOLD = 0.15  # 重新平衡阈值

    # 资金管理参数
    TOTAL_CAPITAL = 100000.0  # 总资金（元）
    MAX_POSITIONS = 4  # 最大同时持仓ETF数量
    DEFAULT_CAPITAL_PER_ETF = 25000.0  # 每个ETF默认分配资金

    # 交易参数
    MIN_TRADE_UNIT = 100  # 最小交易单位（手）
    COMMISSION_RATE = 0.0003  # 佣金费率
    MIN_COMMISSION = 5.0  # 最小佣金

    # 回测参数
    BACKTEST_START_DATE = "2020-01-01"
    BACKTEST_END_DATE = datetime.now().strftime("%Y-%m-%d")
    SLIPPAGE_BPS = 2  # 滑点（基点）

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            attr: getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith('_') and not callable(getattr(cls, attr))
        }

    @classmethod
    def update_config(cls, updates: Dict[str, Any]) -> None:
        """更新配置"""
        for key, value in updates.items():
            if hasattr(cls, key):
                setattr(cls, key, value)
            else:
                raise ValueError(f"未知的配置参数: {key}")

# 市场状态枚举
class MarketStatus:
    CLOSED = "CLOSED"
    PRE_TRADING = "PRE_TRADING"
    TRADING = "TRADING"
    LUNCH_BREAK = "LUNCH_BREAK"
    AFTER_TRADING = "AFTER_TRADING"

# 交易方向枚举
class Direction:
    BUY = "BUY"
    SELL = "SELL"

# 订单状态枚举
class OrderStatus:
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

# 持仓类型枚举
class PositionType:
    LONG = "LONG"
    SHORT = "SHORT"  # ETF通常不允许做空，但为扩展性保留

# 数据频率
class DataFrequency:
    TICK = "tick"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1M"

class ETFGridConfig:
    """ETF网格交易配置类"""

    def __init__(self):
        # 数据路径配置
        self.qmt_data_dir = r"C:\Users\zhanghang\国金证券QMT交易端\datadir"

        # 通用配置
        self.session_id = 123456  # QMT会话ID
        self.enable_risk_control = True  # 启用风险控制
        self.enable_backtest = True  # 启用回测功能
        self.max_position_ratio = 0.8  # 最大仓位比例
        self.max_single_loss = 0.02  # 单次最大损失比例

        # ETF标的配置（从Table.xls解析）
        self.etf_universe = self._parse_table_config()

    def _parse_table_config(self) -> List[Dict]:
        """
        解析Table.xls中的ETF配置
        返回ETF配置列表
        """
        etf_configs = []

        # 从Table.xls解析的配置数据
        table_data = [
            {
                "etf_code": "159682",
                "etf_name": "半导体ETF",
                "base_price": 1.408,
                "up_trigger": 0.05,  # 上涨5%触发卖出
                "down_trigger": 0.05,  # 下跌5%触发买入
                "buy_amount": 20000,  # 每次买入金额
                "sell_amount": 20000,  # 每次卖出金额
                "valid_until": "2026-01-01",
                "account_type": "普通账户"
            },
            {
                "etf_code": "159380",
                "etf_name": "A500指数",
                "base_price": 1.237,
                "up_trigger": 0.05,
                "down_trigger": 0.05,
                "buy_amount": 60000,
                "sell_amount": 10000,
                "valid_until": "2025-12-21",
                "account_type": "普通账户"
            },
            {
                "etf_code": "159985",
                "etf_name": "液晶ETF",
                "base_price": 2.032,
                "up_trigger": 0.05,
                "down_trigger": 0.10,
                "buy_amount": 50000,
                "sell_amount": 50000,
                "valid_until": "2025-12-14",
                "account_type": "普通账户"
            },
            {
                "etf_code": "159937",
                "etf_name": "平安9999",
                "base_price": 8.990,
                "up_trigger": 0.05,
                "down_trigger": 0.05,
                "buy_amount": 45000,
                "sell_amount": 50000,
                "valid_until": "2026-02-21",
                "account_type": "普通账户"
            },
            {
                "etf_code": "513730",
                "etf_name": "通信 ETF",
                "base_price": 1.467,
                "up_trigger": 0.05,
                "down_trigger": 0.08,
                "buy_amount": 20000,
                "sell_amount": 20000,
                "valid_until": "2026-09-05",
                "account_type": "普通账户"
            },
            {
                "etf_code": "513130",
                "etf_name": "纳斯达克",
                "base_price": 0.741,
                "up_trigger": 0.05,
                "down_trigger": 0.05,
                "buy_amount": 45000,
                "sell_amount": 50000,
                "valid_until": "2026-09-05",
                "account_type": "普通账户"
            }
        ]

        for config in table_data:
            # 为每个ETF生成网格层级
            etf_config = {
                "etf_code": config["etf_code"],
                "etf_name": config["etf_name"],
                "base_price": config["base_price"],
                "up_trigger": config["up_trigger"],
                "down_trigger": config["down_trigger"],
                "buy_amount": config["buy_amount"],
                "sell_amount": config["sell_amount"],
                "valid_until": config["valid_until"],
                "account_type": config["account_type"],
                "grid_levels": self._generate_grid_levels(config),
                "position_limits": self._calculate_position_limits(config)
            }
            etf_configs.append(etf_config)

        return etf_configs

    def _generate_grid_levels(self, config: Dict, grid_count: int = 10) -> List[Dict]:
        """
        生成网格层级
        grid_count: 网格层数（默认10层）
        """
        levels = []
        base_price = config["base_price"]
        up_trigger = config["up_trigger"]
        down_trigger = config["down_trigger"]

        # 生成上涨网格（卖出网格）
        for i in range(1, grid_count // 2 + 1):
            price = base_price * (1 + up_trigger * i)
            levels.append({
                "level": i,
                "price": round(price, 3),  # 保留3位小数
                "direction": "sell",  # 上涨时卖出
                "trigger_ratio": up_trigger * i,
                "amount": config["sell_amount"]
            })

        # 生成下跌网格（买入网格）
        for i in range(1, grid_count // 2 + 1):
            price = base_price * (1 - down_trigger * i)
            levels.append({
                "level": -i,
                "price": round(price, 3),
                "direction": "buy",  # 下跌时买入
                "trigger_ratio": down_trigger * i,
                "amount": config["buy_amount"]
            })

        # 按价格排序
        levels.sort(key=lambda x: x["price"])
        return levels

    def _calculate_position_limits(self, config: Dict) -> Dict:
        """计算仓位限制"""
        total_investment = config["buy_amount"] * 5  # 假设最多投入5次买入金额
        return {
            "max_total_investment": total_investment,
            "max_single_order": max(config["buy_amount"], config["sell_amount"]),
            "min_holding_ratio": 0.1,  # 最小持仓比例
            "max_holding_ratio": 0.3   # 最大持仓比例
        }

    def get_etf_config(self, etf_code: str) -> Optional[Dict]:
        """根据ETF代码获取配置"""
        for config in self.etf_universe:
            if config["etf_code"] == etf_code:
                return config
        return None

    def is_valid_etf(self, etf_code: str) -> bool:
        """检查ETF是否在有效范围内"""
        config = self.get_etf_config(etf_code)
        if not config:
            return False

        # 检查有效期
        from datetime import datetime
        valid_until = datetime.strptime(config["valid_until"], "%Y-%m-%d")
        return datetime.now() <= valid_until


class RiskManagementConfig:
    """风险管理配置"""

    def __init__(self):
        # 单日风险限制
        self.max_daily_loss = 0.05  # 单日最大亏损比例5%
        self.max_daily_trades = 50  # 单日最大交易次数

        # 单笔交易风险限制
        self.max_single_order_ratio = 0.1  # 单笔订单最大资金占比
        self.max_slippage = 0.002  # 最大滑点0.2%

        # 仓位风险限制
        self.max_total_position = 0.8  # 最大总仓位80%
        self.max_single_etf_position = 0.3  # 单个ETF最大仓位30%

        # 止损止盈
        self.stop_loss_ratio = 0.15  # 止损比例15%
        self.take_profit_ratio = 0.20  # 止盈比例20%

        # 流动性风险
        self.min_trading_volume = 1000000  # 最小日成交额100万元
        self.max_entrust_ratio = 0.1  # 最大委托比例10%


class BacktestConfig:
    """回测配置"""

    def __init__(self):
        self.start_date = "2024-01-01"
        self.end_date = "2024-12-31"
        self.initial_capital = 1000000  # 初始资金100万
        self.commission_rate = 0.0003  # 手续费率0.03%
        self.slippage_rate = 0.001  # 滑点率0.1%
        self.enable_benchmark = True  # 启用基准比较
        self.benchmark_index = "000300"  # 沪深300作为基准


# 全局配置实例
CONFIG = TradingConfig()
ETF_GRID_CONFIG = ETFGridConfig()
RISK_CONFIG = RiskManagementConfig()
BACKTEST_CONFIG = BacktestConfig()

# 确保日志目录存在
os.makedirs(os.path.dirname(CONFIG.LOG_FILE), exist_ok=True)