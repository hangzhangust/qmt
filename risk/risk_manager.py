"""
ETF网格交易风险管理器
实现全面的风险控制和监控功能
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import time

from config.settings import TradingConfig, RISK_CONFIG
from utils.logger import get_logger

class RiskLevel(Enum):
    """风险等级"""
    LOW = "LOW"           # 低风险
    MEDIUM = "MEDIUM"     # 中等风险
    HIGH = "HIGH"         # 高风险
    CRITICAL = "CRITICAL" # 严重风险

class RiskType(Enum):
    """风险类型"""
    POSITION = "POSITION"         # 仓位风险
    DAILY_LOSS = "DAILY_LOSS"     # 日损失风险
    DRAWDOWN = "DRAWDOWN"         # 回撤风险
    CONCENTRATION = "CONCENTRATION" # 集中度风险
    LIQUIDITY = "LIQUIDITY"       # 流动性风险
    MARKET = "MARKET"             # 市场风险

@dataclass
class RiskAlert:
    """风险告警"""
    risk_type: RiskType
    risk_level: RiskLevel
    symbol: str
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    action_required: bool = False

class ETFGridRiskManager:
    """ETF网格交易风险管理器"""

    def __init__(self, total_capital: float):
        """
        初始化风险管理器

        Args:
            total_capital: 总资金
        """
        self.total_capital = total_capital
        self.logger = get_logger("ETFGridRiskManager")

        # 风险限制
        self.max_daily_loss = RISK_CONFIG.max_daily_loss
        self.max_single_order_ratio = RISK_CONFIG.max_single_order_ratio
        self.max_total_position = RISK_CONFIG.max_total_position
        self.max_single_etf_position = RISK_CONFIG.max_single_etf_position
        self.stop_loss_ratio = RISK_CONFIG.stop_loss_ratio
        self.take_profit_ratio = RISK_CONFIG.take_profit_ratio

        # 状态跟踪
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_drawdown = 0.0
        self.peak_capital = total_capital
        self.current_capital = total_capital

        # 持仓和风险监控
        self.positions = {}  # ETF持仓信息
        self.risk_alerts = []  # 风险告警列表
        self.risk_metrics = {}  # 风险指标

        # 线程锁
        self._lock = threading.RLock()

        # 统计信息
        self.risk_stats = {
            'total_alerts': 0,
            'critical_alerts': 0,
            'high_alerts': 0,
            'emergency_stops': 0,
            'last_risk_check': None
        }

        self.logger.info(f"ETF风险管理器初始化完成，总资金: {total_capital:,.2f}")

    def check_pre_trade_risk(self,
                           symbol: str,
                           action: str,
                           quantity: int,
                           price: float) -> Tuple[bool, List[str]]:
        """
        交易前风险检查

        Args:
            symbol: ETF代码
            action: 买卖方向
            quantity: 数量
            price: 价格

        Returns:
            (是否通过, 风险信息列表)
        """
        try:
            with self._lock:
                risk_messages = []

                # 计算交易金额
                trade_amount = quantity * price
                trade_ratio = trade_amount / self.total_capital

                # 1. 检查单笔订单金额限制
                if trade_ratio > self.max_single_order_ratio:
                    risk_messages.append(
                        f"单笔订单金额超限: {trade_ratio:.2%} > {self.max_single_order_ratio:.2%}"
                    )

                # 2. 检查日交易次数限制
                max_daily_trades = RISK_CONFIG.max_daily_trades
                if self.daily_trades >= max_daily_trades:
                    risk_messages.append(
                        f"日交易次数超限: {self.daily_trades} >= {max_daily_trades}"
                    )

                # 3. 检查仓位限制
                position_risk = self._check_position_limits(symbol, action, trade_amount)
                risk_messages.extend(position_risk)

                # 4. 检查日损失限制
                loss_risk = self._check_daily_loss_limit()
                risk_messages.extend(loss_risk)

                # 5. 检查集中度风险
                concentration_risk = self._check_concentration_risk(symbol, action, trade_amount)
                risk_messages.extend(concentration_risk)

                # 6. 检查市场风险
                market_risk = self._check_market_risk(symbol)
                risk_messages.extend(market_risk)

                # 判断是否通过风险检查
                passed = len(risk_messages) == 0

                if not passed:
                    self.logger.warning(f"交易风险检查未通过: {symbol} {action}, 风险: {risk_messages}")

                return passed, risk_messages

        except Exception as e:
            self.logger.error(f"交易前风险检查异常: {str(e)}")
            return False, [f"风险检查异常: {str(e)}"]

    def _check_position_limits(self, symbol: str, action: str, trade_amount: float) -> List[str]:
        """检查仓位限制"""
        messages = []

        try:
            current_position = self.positions.get(symbol, {}).get('quantity', 0)
            current_value = self.positions.get(symbol, {}).get('value', 0)

            if action == "BUY":
                # 买入后的仓位
                new_position_value = current_value + trade_amount
                new_position_ratio = new_position_value / self.total_capital

                # 检查单个ETF仓位限制
                if new_position_ratio > self.max_single_etf_position:
                    messages.append(
                        f"单个ETF仓位超限: {new_position_ratio:.2%} > {self.max_single_etf_position:.2%}"
                    )

                # 检查总仓位限制
                current_total_position = sum(p.get('value', 0) for p in self.positions.values())
                new_total_position = current_total_position + trade_amount
                total_position_ratio = new_total_position / self.total_capital

                if total_position_ratio > self.max_total_position:
                    messages.append(
                        f"总仓位超限: {total_position_ratio:.2%} > {self.max_total_position:.2%}"
                    )

        except Exception as e:
            messages.append(f"仓位检查异常: {str(e)}")

        return messages

    def _check_daily_loss_limit(self) -> List[str]:
        """检查日损失限制"""
        messages = []

        try:
            daily_loss_ratio = abs(self.daily_pnl) / self.total_capital

            if self.daily_pnl < 0 and daily_loss_ratio > self.max_daily_loss:
                messages.append(
                    f"日损失超限: {daily_loss_ratio:.2%} > {self.max_daily_loss:.2%}"
                )

        except Exception as e:
            messages.append(f"日损失检查异常: {str(e)}")

        return messages

    def _check_concentration_risk(self, symbol: str, action: str, trade_amount: float) -> List[str]:
        """检查集中度风险"""
        messages = []

        try:
            # 计算行业/板块集中度（简化版本）
            total_value = sum(p.get('value', 0) for p in self.positions.values())
            if action == "BUY":
                new_total_value = total_value + trade_amount
            else:
                new_total_value = total_value - trade_amount

            concentration_ratio = new_total_value / self.total_capital

            if concentration_ratio > 0.9:  # 90%集中度警告
                messages.append(
                    f"集中度过高: {concentration_ratio:.2%} > 90%"
                )

        except Exception as e:
            messages.append(f"集中度检查异常: {str(e)}")

        return messages

    def _check_market_risk(self, symbol: str) -> List[str]:
        """检查市场风险"""
        messages = []

        try:
            # 这里可以添加市场风险指标检查
            # 如波动率、流动性等

            # 检查交易时间（避免在重大事件期间交易）
            current_time = datetime.now().time()
            market_close = datetime.strptime("15:00", "%H:%M").time()
            market_open = datetime.strptime("09:30", "%H:%M").time()

            if current_time > market_close or current_time < market_open:
                messages.append("非交易时间")

        except Exception as e:
            messages.append(f"市场风险检查异常: {str(e)}")

        return messages

    def update_position(self,
                       symbol: str,
                       quantity: int,
                       price: float,
                       action: str,
                       commission: float = 0):
        """
        更新持仓信息

        Args:
            symbol: ETF代码
            quantity: 数量
            price: 价格
            action: 买卖方向
            commission: 手续费
        """
        try:
            with self._lock:
                trade_value = quantity * price

                if symbol not in self.positions:
                    self.positions[symbol] = {
                        'quantity': 0,
                        'avg_price': 0.0,
                        'cost_basis': 0.0,
                        'value': 0.0,
                        'unrealized_pnl': 0.0,
                        'realized_pnl': 0.0
                    }

                position = self.positions[symbol]

                if action == "BUY":
                    # 买入
                    old_quantity = position['quantity']
                    old_cost = position['cost_basis']

                    new_quantity = old_quantity + quantity
                    new_cost = old_cost + trade_value
                    new_avg_price = new_cost / new_quantity if new_quantity > 0 else 0.0

                    position['quantity'] = new_quantity
                    position['avg_price'] = new_avg_price
                    position['cost_basis'] = new_cost
                    position['value'] = new_cost

                    # 更新总资金
                    self.current_capital -= (trade_value + commission)

                else:  # SELL
                    # 卖出
                    if position['quantity'] >= quantity:
                        sell_cost_basis = position['avg_price'] * quantity
                        realized_pnl = trade_value - sell_cost_basis - commission

                        position['quantity'] -= quantity
                        position['realized_pnl'] += realized_pnl

                        # 如果全部卖出，清空持仓
                        if position['quantity'] == 0:
                            position['cost_basis'] = 0.0
                            position['avg_price'] = 0.0
                        else:
                            position['cost_basis'] -= sell_cost_basis

                        position['value'] = position['cost_basis']

                        # 更新总资金和日盈亏
                        self.current_capital += (trade_value - commission)
                        self.daily_pnl += realized_pnl

                # 更新交易统计
                self.daily_trades += 1

                self.logger.debug(f"持仓更新: {symbol} {action} {quantity}股 @¥{price:.3f}")

        except Exception as e:
            self.logger.error(f"持仓更新异常: {str(e)}")

    def update_market_data(self, symbol: str, current_price: float):
        """
        更新市场数据并计算风险指标

        Args:
            symbol: ETF代码
            current_price: 当前价格
        """
        try:
            with self._lock:
                if symbol in self.positions:
                    position = self.positions[symbol]
                    if position['quantity'] > 0:
                        # 计算未实现盈亏
                        market_value = position['quantity'] * current_price
                        unrealized_pnl = market_value - position['cost_basis']

                        position['value'] = market_value
                        position['unrealized_pnl'] = unrealized_pnl

            # 计算总风险指标
            self._calculate_risk_metrics()

            # 检查风险告警
            self._check_risk_alerts()

        except Exception as e:
            self.logger.error(f"市场数据更新异常: {str(e)}")

    def _calculate_risk_metrics(self):
        """计算风险指标"""
        try:
            with self._lock:
                # 计算总资产
                total_positions_value = sum(p.get('value', 0) for p in self.positions.values())
                total_value = self.current_capital + total_positions_value

                # 计算日收益率
                daily_return = (total_value - self.peak_capital) / self.peak_capital

                # 更新峰值和回撤
                if total_value > self.peak_capital:
                    self.peak_capital = total_value

                current_drawdown = (self.peak_capital - total_value) / self.peak_capital
                self.max_drawdown = max(self.max_drawdown, current_drawdown)

                # 计算风险指标
                self.risk_metrics = {
                    'total_value': total_value,
                    'daily_return': daily_return,
                    'max_drawdown': self.max_drawdown,
                    'current_drawdown': current_drawdown,
                    'position_ratio': total_positions_value / total_value if total_value > 0 else 0,
                    'daily_pnl': self.daily_pnl,
                    'daily_trades': self.daily_trades,
                    'cash_ratio': self.current_capital / total_value if total_value > 0 else 0,
                }

        except Exception as e:
            self.logger.error(f"计算风险指标异常: {str(e)}")

    def _check_risk_alerts(self):
        """检查风险告警"""
        try:
            if not self.risk_metrics:
                return

            alerts = []

            # 1. 检查日损失风险
            if self.daily_pnl < 0:
                loss_ratio = abs(self.daily_pnl) / self.total_capital
                if loss_ratio > self.max_daily_loss:
                    alerts.append(RiskAlert(
                        risk_type=RiskType.DAILY_LOSS,
                        risk_level=RiskLevel.CRITICAL,
                        symbol="ALL",
                        message=f"日损失超限: {loss_ratio:.2%}",
                        current_value=loss_ratio,
                        threshold=self.max_daily_loss,
                        timestamp=datetime.now(),
                        action_required=True
                    ))

            # 2. 检查回撤风险
            if self.risk_metrics['current_drawdown'] > 0.1:  # 10%回撤警告
                alerts.append(RiskAlert(
                    risk_type=RiskType.DRAWDOWN,
                    risk_level=RiskLevel.HIGH,
                    symbol="ALL",
                    message=f"回撤过大: {self.risk_metrics['current_drawdown']:.2%}",
                    current_value=self.risk_metrics['current_drawdown'],
                    threshold=0.1,
                    timestamp=datetime.now(),
                    action_required=False
                ))

            # 3. 检查仓位风险
            if self.risk_metrics['position_ratio'] > 0.9:  # 90%仓位警告
                alerts.append(RiskAlert(
                    risk_type=RiskType.POSITION,
                    risk_level=RiskLevel.MEDIUM,
                    symbol="ALL",
                    message=f"仓位过高: {self.risk_metrics['position_ratio']:.2%}",
                    current_value=self.risk_metrics['position_ratio'],
                    threshold=0.9,
                    timestamp=datetime.now(),
                    action_required=False
                ))

            # 4. 检查单个ETF仓位
            for symbol, position in self.positions.items():
                if position['value'] > 0:
                    position_ratio = position['value'] / self.total_capital
                    if position_ratio > self.max_single_etf_position:
                        alerts.append(RiskAlert(
                            risk_type=RiskType.CONCENTRATION,
                            risk_level=RiskLevel.MEDIUM,
                            symbol=symbol,
                            message=f"单个ETF仓位过高: {position_ratio:.2%}",
                            current_value=position_ratio,
                            threshold=self.max_single_etf_position,
                            timestamp=datetime.now(),
                            action_required=False
                        ))

            # 保存告警
            if alerts:
                self.risk_alerts.extend(alerts)
                self.risk_stats['total_alerts'] += len(alerts)
                self.risk_stats['critical_alerts'] += sum(1 for a in alerts if a.risk_level == RiskLevel.CRITICAL)
                self.risk_stats['high_alerts'] += sum(1 for a in alerts if a.risk_level == RiskLevel.HIGH)
                self.risk_stats['last_risk_check'] = datetime.now()

                # 记录日志
                for alert in alerts:
                    self.logger.warning(f"风险告警: {alert.risk_type.value} - {alert.message}")

        except Exception as e:
            self.logger.error(f"风险告警检查异常: {str(e)}")

    def get_risk_status(self) -> Dict[str, Any]:
        """获取风险状态"""
        with self._lock:
            # 计算风险等级
            risk_level = self._calculate_overall_risk_level()

            return {
                'risk_level': risk_level.value,
                'risk_metrics': self.risk_metrics.copy(),
                'positions': {k: v.copy() for k, v in self.positions.items()},
                'recent_alerts': [self._alert_to_dict(a) for a in self.risk_alerts[-10:]],
                'risk_stats': self.risk_stats.copy(),
                'limits': {
                    'max_daily_loss': self.max_daily_loss,
                    'max_single_order_ratio': self.max_single_order_ratio,
                    'max_total_position': self.max_total_position,
                    'max_single_etf_position': self.max_single_etf_position
                }
            }

    def _calculate_overall_risk_level(self) -> RiskLevel:
        """计算整体风险等级"""
        try:
            # 检查是否有严重风险
            critical_alerts = [a for a in self.risk_alerts if a.risk_level == RiskLevel.CRITICAL]
            if critical_alerts:
                return RiskLevel.CRITICAL

            # 检查高风险指标
            if self.risk_metrics.get('current_drawdown', 0) > 0.15:  # 15%回撤
                return RiskLevel.CRITICAL

            if abs(self.risk_metrics.get('daily_pnl', 0)) / self.total_capital > 0.08:  # 8%日损失
                return RiskLevel.CRITICAL

            # 检查高风险
            high_alerts = [a for a in self.risk_alerts if a.risk_level == RiskLevel.HIGH]
            if high_alerts:
                return RiskLevel.HIGH

            if self.risk_metrics.get('position_ratio', 0) > 0.8:  # 80%仓位
                return RiskLevel.HIGH

            # 检查中等风险
            medium_alerts = [a for a in self.risk_alerts if a.risk_level == RiskLevel.MEDIUM]
            if medium_alerts:
                return RiskLevel.MEDIUM

            # 默认低风险
            return RiskLevel.LOW

        except Exception as e:
            self.logger.error(f"计算风险等级异常: {str(e)}")
            return RiskLevel.HIGH

    def _alert_to_dict(self, alert: RiskAlert) -> Dict[str, Any]:
        """将告警对象转换为字典"""
        return {
            'risk_type': alert.risk_type.value,
            'risk_level': alert.risk_level.value,
            'symbol': alert.symbol,
            'message': alert.message,
            'current_value': alert.current_value,
            'threshold': alert.threshold,
            'timestamp': alert.timestamp.isoformat(),
            'action_required': alert.action_required
        }

    def should_stop_trading(self) -> bool:
        """判断是否应该停止交易"""
        try:
            with self._lock:
                # 检查严重风险
                critical_alerts = [a for a in self.risk_alerts if a.risk_level == RiskLevel.CRITICAL]

                if critical_alerts:
                    for alert in critical_alerts:
                        if alert.action_required:
                            self.logger.critical(f"触发紧急停止: {alert.message}")
                            self.risk_stats['emergency_stops'] += 1
                            return True

                # 检查关键风险指标
                if abs(self.daily_pnl) / self.total_capital > self.max_daily_loss:
                    self.logger.critical("日损失超限，触发紧急停止")
                    self.risk_stats['emergency_stops'] += 1
                    return True

                if self.risk_metrics.get('current_drawdown', 0) > 0.2:  # 20%回撤
                    self.logger.critical("回撤过大，触发紧急停止")
                    self.risk_stats['emergency_stops'] += 1
                    return True

                return False

        except Exception as e:
            self.logger.error(f"判断交易停止异常: {str(e)}")
            return True  # 出错时停止交易

    def reset_daily_stats(self):
        """重置日统计"""
        with self._lock:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.logger.info("日统计已重置")

    def clear_old_alerts(self, days: int = 7):
        """清理旧的告警记录"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            self.risk_alerts = [a for a in self.risk_alerts if a.timestamp > cutoff_time]
            self.logger.info(f"清理了 {days} 天前的告警记录")
        except Exception as e:
            self.logger.error(f"清理告警记录异常: {str(e)}")