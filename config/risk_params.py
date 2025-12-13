"""
风险管理参数配置
定义所有风险控制相关的参数和规则
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    AGGRESSIVE = "aggressive"

@dataclass
class RiskLimits:
    """风险限制参数"""
    # 资金管理
    max_position_pct: float = 0.20      # 单个ETF最大持仓比例
    max_total_position_pct: float = 0.80 # 总持仓比例
    daily_loss_limit_pct: float = 0.05  # 日内亏损限制
    max_drawdown_pct: float = 0.15      # 最大回撤限制

    # 持仓管理
    max_positions: int = 4              # 最大同时持仓数量
    min_trade_interval: int = 60        # 最小交易间隔（秒）
    max_trades_per_day: int = 20        # 每日最大交易次数

    # 单笔交易限制
    max_single_trade_amount: float = 50000.0  # 单笔最大交易金额
    min_trade_amount: float = 1000.0          # 单笔最小交易金额
    position_size_pct: float = 0.05           # 单网格仓位大小（占ETF资金的比例）

    # 止损设置
    stop_loss_pct: float = 0.05        # 止损比例
    take_profit_pct: float = 0.10     # 止盈比例
    trailing_stop_pct: float = 0.03   # 移动止损比例

    # 流动性过滤
    min_avg_volume: float = 1000000.0  # 最小平均成交量（元）
    max_volatility: float = 0.05      # 最大波动率（日）

    # 时间控制
    max_holding_days: int = 30         # 最大持仓天数
    position_review_interval: int = 300  # 持仓检查间隔（秒）

class RiskManagerConfig:
    """风险管理配置"""

    # 不同风险等级的预设参数
    RISK_PROFILES = {
        RiskLevel.LOW: RiskLimits(
            max_position_pct=0.10,
            daily_loss_limit_pct=0.02,
            max_drawdown_pct=0.08,
            max_positions=3,
            position_size_pct=0.03,
            stop_loss_pct=0.03,
        ),
        RiskLevel.MEDIUM: RiskLimits(
            max_position_pct=0.20,
            daily_loss_limit_pct=0.05,
            max_drawdown_pct=0.15,
            max_positions=4,
            position_size_pct=0.05,
            stop_loss_pct=0.05,
        ),
        RiskLevel.HIGH: RiskLimits(
            max_position_pct=0.25,
            daily_loss_limit_pct=0.08,
            max_drawdown_pct=0.20,
            max_positions=5,
            position_size_pct=0.08,
            stop_loss_pct=0.08,
        ),
        RiskLevel.AGGRESSIVE: RiskLimits(
            max_position_pct=0.30,
            daily_loss_limit_pct=0.10,
            max_drawdown_pct=0.25,
            max_positions=6,
            position_size_pct=0.10,
            stop_loss_pct=0.10,
        ),
    }

    # 当前风险等级
    current_risk_level = RiskLevel.MEDIUM

    @classmethod
    def get_current_limits(cls) -> RiskLimits:
        """获取当前风险等级的限制"""
        return cls.RISK_PROFILES[cls.current_risk_level]

    @classmethod
    def set_risk_level(cls, level: RiskLevel) -> None:
        """设置风险等级"""
        cls.current_risk_level = level

    @classmethod
    def update_limits(cls, updates: Dict[str, Any]) -> None:
        """更新风险限制参数"""
        current_limits = cls.get_current_limits()
        for key, value in updates.items():
            if hasattr(current_limits, key):
                setattr(current_limits, key, value)
            else:
                raise ValueError(f"未知的风险参数: {key}")

class GridRiskParams:
    """网格交易特定风险参数"""

    # 网格设置
    max_grid_levels: int = 30          # 最大网格层数
    min_grid_levels: int = 10          # 最小网格层数
    max_grid_spacing_pct: float = 0.10 # 最大网格间距
    min_grid_spacing_pct: float = 0.005 # 最小网格间距

    # 网格重新平衡
    rebalance_threshold_pct: float = 0.15  # 重新平衡阈值
    rebalance_check_interval: int = 300    # 重新平衡检查间隔（秒）

    # 网格风险控制
    max_grid_positions: int = 10       # 单个ETF最大网格持仓数量
    grid_stop_loss_pct: float = 0.08   # 网格策略止损比例
    max_grid_exposure_pct: float = 0.40 # 单个ETF最大网格敞口

class MarketRiskParams:
    """市场风险参数"""

    # 市场状态监控
    market_volatility_threshold: float = 0.03  # 市场波动率阈值
    market_trend_change_threshold: float = 0.02 # 市场趋势变化阈值

    # 暴跌/暴涨保护
    circuit_breaker_threshold: float = 0.07  # 熔断阈值
    market_crash_threshold: float = 0.05     # 市场暴跌阈值

    # 相关性控制
    max_correlation: float = 0.8            # 最大相关性
    sector_exposure_limit: float = 0.6      # 行业敞口限制

class AlertThresholds:
    """警报阈值设置"""

    # 资金警报
    low_cash_threshold: float = 10000.0     # 低资金警报
    margin_call_threshold: float = 0.8      # 追加保证金警报

    # 持仓警报
    large_position_threshold: float = 0.15  # 大额持仓警报
    concentration_alert_threshold: float = 0.4  # 持仓集中度警报

    # 交易警报
    frequent_trading_threshold: int = 10    # 频繁交易警报（小时）
    large_order_threshold: float = 50000.0  # 大额订单警报

# 风险管理全局配置实例
RISK_CONFIG = RiskManagerConfig()
GRID_RISK_PARAMS = GridRiskParams()
MARKET_RISK_PARAMS = MarketRiskParams()
ALERT_THRESHOLDS = AlertThresholds()

# 导出主要配置
def get_all_risk_params() -> Dict[str, Any]:
    """获取所有风险参数"""
    return {
        "risk_limits": RISK_CONFIG.get_current_limits(),
        "grid_risk": GRID_RISK_PARAMS,
        "market_risk": MARKET_RISK_PARAMS,
        "alerts": ALERT_THRESHOLDS,
        "risk_level": RISK_CONFIG.current_risk_level.value,
    }

def validate_risk_params() -> List[str]:
    """验证风险参数的合理性"""
    issues = []
    limits = RISK_CONFIG.get_current_limits()

    if limits.max_position_pct > 0.5:
        issues.append("单ETF持仓比例过高 (>50%)")

    if limits.daily_loss_limit_pct > 0.15:
        issues.append("日内亏损限制过高 (>15%)")

    if limits.max_drawdown_pct > 0.30:
        issues.append("最大回撤限制过高 (>30%)")

    if limits.position_size_pct < 0.01:
        issues.append("网格仓位过小 (<1%)")

    if limits.position_size_pct > 0.20:
        issues.append("网格仓位过大 (>20%)")

    return issues