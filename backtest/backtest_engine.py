"""
ETF网格交易回测引擎
基于历史数据对网格交易策略进行回测分析
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from strategy.grid_engine import ETFGridStrategy
from config.settings import BACKTEST_CONFIG, ETF_GRID_CONFIG
from data.xtquant_client import XtQuantClient
from utils.logger import get_logger

@dataclass
class BacktestResult:
    """回测结果"""
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_trades: int
    loss_trades: int
    avg_profit: float
    avg_loss: float
    profit_factor: float
    total_commission: float
    trades_history: List[Dict[str, Any]] = field(default_factory=list)
    daily_returns: pd.Series = field(default_factory=lambda: pd.Series())
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series())

class ETFGridBacktestEngine:
    """ETF网格交易回测引擎"""

    def __init__(self, initial_capital: float = None):
        """
        初始化回测引擎

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital or BACKTEST_CONFIG.initial_capital
        self.commission_rate = BACKTEST_CONFIG.commission_rate
        self.slippage_rate = BACKTEST_CONFIG.slippage_rate
        self.logger = get_logger("ETFGridBacktestEngine")

        # 数据客户端
        self.data_client = None
        try:
            self.data_client = XtQuantClient()
            if not self.data_client.connect():
                self.logger.warning("XtQuant连接失败，将使用模拟数据")
        except Exception as e:
            self.logger.warning(f"XtQuant初始化失败: {str(e)}")

        self.logger.info(f"ETF网格回测引擎初始化完成，初始资金: {self.initial_capital:,.2f}")

    def run_backtest(self,
                    etf_code: str,
                    start_date: str = None,
                    end_date: str = None,
                    capital: float = None) -> BacktestResult:
        """
        运行网格交易回测

        Args:
            etf_code: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            capital: 分配资金

        Returns:
            回测结果
        """
        start_date = start_date or BACKTEST_CONFIG.start_date
        end_date = end_date or BACKTEST_CONFIG.end_date
        capital = capital or (self.initial_capital / 6)  # 默认分配1/6资金

        self.logger.info(f"开始回测 {etf_code} ({start_date} 至 {end_date}), 资金: {capital:,.2f}")

        try:
            # 获取历史数据
            hist_data = self._get_historical_data(etf_code, start_date, end_date)
            if hist_data.empty:
                raise ValueError(f"无法获取 {etf_code} 的历史数据")

            # 初始化策略
            strategy = self._initialize_strategy(etf_code, capital, hist_data)

            # 运行回测
            result = self._run_simulation(strategy, hist_data, capital)

            # 计算性能指标
            result = self._calculate_performance_metrics(result)

            self.logger.info(f"回测完成 {etf_code}: 总收益率 {result.total_return:.2%}, "
                           f"年化收益率 {result.annual_return:.2%}, 夏普比率 {result.sharpe_ratio:.2f}")

            return result

        except Exception as e:
            self.logger.error(f"回测失败 {etf_code}: {str(e)}")
            raise

    def _get_historical_data(self, etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取历史数据"""
        try:
            if self.data_client and self.data_client.is_connected:
                # 使用XtQuant获取真实数据
                data = self.data_client.get_local_data(
                    stock_list=[etf_code],
                    field_list=['open', 'high', 'low', 'close', 'volume'],
                    period='1d',
                    start_time=start_date,
                    end_time=end_date,
                    count=-1
                )

                if data and etf_code in data:
                    df = data[etf_code]
                    if isinstance(df, dict):
                        df = pd.DataFrame(df)
                    df.index = pd.to_datetime(df.index)
                    return df

            # 生成模拟数据
            return self._generate_simulated_data(etf_code, start_date, end_date)

        except Exception as e:
            self.logger.warning(f"获取真实数据失败，使用模拟数据: {str(e)}")
            return self._generate_simulated_data(etf_code, start_date, end_date)

    def _generate_simulated_data(self, etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模拟历史数据"""
        # 获取ETF配置
        etf_config = ETF_GRID_CONFIG.get_etf_config(etf_code)
        if not etf_config:
            raise ValueError(f"未找到ETF配置: {etf_code}")

        base_price = etf_config['base_price']
        volatility = 0.02  # 日波动率2%
        drift = 0.0002  # 日均漂移0.02%

        # 生成日期范围
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        dates = pd.bdate_range(start, end)

        # 生成价格序列
        np.random.seed(42)  # 固定种子以确保可重复性
        returns = np.random.normal(drift, volatility, len(dates))
        prices = [base_price]

        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            # 确保价格为正
            new_price = max(new_price, base_price * 0.3)
            prices.append(new_price)

        # 生成OHLCV数据
        data = []
        for i, (date, close_price) in enumerate(zip(dates, prices)):
            # 生成日内高低开价
            intraday_vol = close_price * volatility * 0.5
            high = close_price + abs(np.random.normal(0, intraday_vol))
            low = close_price - abs(np.random.normal(0, intraday_vol))

            # 确保高低开价关系正确
            high = max(high, close_price)
            low = min(low, close_price)

            # 开盘价在前一日收盘价附近
            if i > 0:
                open_price = prices[i-1] + np.random.normal(0, intraday_vol * 0.3)
            else:
                open_price = close_price

            open_price = max(min(open_price, high), low)

            # 生成成交量
            volume = int(np.random.normal(1000000, 200000))
            volume = max(volume, 100000)

            data.append({
                'open': round(open_price, 3),
                'high': round(high, 3),
                'low': round(low, 3),
                'close': round(close_price, 3),
                'volume': volume
            })

        df = pd.DataFrame(data, index=dates)
        return df

    def _initialize_strategy(self, etf_code: str, capital: float, hist_data: pd.DataFrame) -> ETFGridStrategy:
        """初始化策略"""
        try:
            # 获取初始价格（使用前10天的平均价格）
            initial_price = hist_data['close'].head(10).mean()

            # 创建策略实例
            strategy = ETFGridStrategy(etf_code, capital)

            # 初始化策略
            if not strategy.initialize(initial_price):
                raise RuntimeError(f"策略初始化失败: {etf_code}")

            return strategy

        except Exception as e:
            self.logger.error(f"策略初始化失败: {str(e)}")
            raise

    def _run_simulation(self, strategy: ETFGridStrategy, hist_data: pd.DataFrame, capital: float) -> BacktestResult:
        """运行回测模拟"""
        # 启动策略
        strategy.start()

        # 初始化结果对象
        result = BacktestResult(
            symbol=strategy.etf_code,
            start_date=hist_data.index[0].strftime('%Y-%m-%d'),
            end_date=hist_data.index[-1].strftime('%Y-%m-%d'),
            initial_capital=capital,
            final_capital=capital,
            total_return=0.0,
            annual_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            total_trades=0,
            profit_trades=0,
            loss_trades=0,
            avg_profit=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            total_commission=0.0
        )

        # 资金曲线数据
        equity_values = []
        daily_returns = []
        positions_value = 0
        cash = capital

        # 模拟交易执行
        for i, (date, row) in enumerate(hist_data.iterrows()):
            current_price = row['close']

            # 更新策略价格
            signals = strategy.update_price(current_price, date)

            # 执行交易信号
            for signal in signals:
                trade_result = self._execute_signal(signal, current_price)
                if trade_result:
                    result.trades_history.append(trade_result)

                    # 更新资金
                    if signal['action'] == 'BUY':
                        trade_cost = trade_result['amount'] + trade_result['commission']
                        cash -= trade_cost
                        positions_value += trade_result['amount']
                    else:  # SELL
                        trade_proceeds = trade_result['amount'] - trade_result['commission']
                        cash += trade_proceeds
                        positions_value -= trade_result['amount']

                    result.total_commission += trade_result['commission']

            # 计算当前总资产
            total_value = cash + positions_value
            equity_values.append(total_value)

            # 计算日收益率
            if i > 0:
                daily_return = (total_value - equity_values[-2]) / equity_values[-2]
                daily_returns.append(daily_return)

        # 创建资金曲线
        result.equity_curve = pd.Series(equity_values, index=hist_data.index)
        result.daily_returns = pd.Series(daily_returns, index=hist_data.index[1:])

        # 计算最终资产
        result.final_capital = equity_values[-1] if equity_values else capital

        # 统计交易信息
        self._analyze_trades(result)

        # 停止策略
        strategy.stop()

        return result

    def _execute_signal(self, signal: Dict[str, Any], market_price: float) -> Optional[Dict[str, Any]]:
        """执行交易信号"""
        try:
            # 计算实际成交价格（考虑滑点）
            if signal['action'] == 'BUY':
                actual_price = market_price * (1 + self.slippage_rate)
            else:  # SELL
                actual_price = market_price * (1 - self.slippage_rate)

            actual_price = round(actual_price, 3)

            # 计算交易金额和手续费
            trade_amount = signal['quantity'] * actual_price
            commission = max(trade_amount * self.commission_rate, 5.0)  # 最低5元手续费

            return {
                'timestamp': signal['timestamp'],
                'action': signal['action'],
                'price': actual_price,
                'quantity': signal['quantity'],
                'amount': trade_amount,
                'commission': commission,
                'signal_type': signal['trigger_type'],
                'grid_level': signal['grid_level']
            }

        except Exception as e:
            self.logger.error(f"执行交易信号失败: {str(e)}")
            return None

    def _analyze_trades(self, result: BacktestResult):
        """分析交易记录"""
        if not result.trades_history:
            return

        buy_trades = [t for t in result.trades_history if t['action'] == 'BUY']
        sell_trades = [t for t in result.trades_history if t['action'] == 'SELL']

        result.total_trades = len(result.trades_history)
        result.profit_trades = len([t for t in sell_trades if t.get('profit', 0) > 0])
        result.loss_trades = len([t for t in sell_trades if t.get('profit', 0) <= 0])

        # 计算平均盈亏
        profits = [t.get('profit', 0) for t in sell_trades if t.get('profit', 0) > 0]
        losses = [t.get('profit', 0) for t in sell_trades if t.get('profit', 0) <= 0]

        result.avg_profit = np.mean(profits) if profits else 0
        result.avg_loss = np.mean(losses) if losses else 0

        # 计算盈亏比
        total_profit = sum(profits)
        total_loss = abs(sum(losses))
        result.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    def _calculate_performance_metrics(self, result: BacktestResult) -> BacktestResult:
        """计算性能指标"""
        try:
            # 总收益率
            result.total_return = (result.final_capital - result.initial_capital) / result.initial_capital

            # 年化收益率
            start_date = pd.to_datetime(result.start_date)
            end_date = pd.to_datetime(result.end_date)
            days = (end_date - start_date).days
            if days > 0:
                result.annual_return = (result.final_capital / result.initial_capital) ** (365.25 / days) - 1

            # 最大回撤
            if not result.equity_curve.empty:
                peak = result.equity_curve.expanding().max()
                drawdown = (result.equity_curve - peak) / peak
                result.max_drawdown = abs(drawdown.min())

            # 夏普比率
            if not result.daily_returns.empty:
                excess_returns = result.daily_returns - 0.03/252  # 假设无风险利率3%
                if excess_returns.std() > 0:
                    result.sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

            # 胜率
            if result.total_trades > 0:
                result.win_rate = result.profit_trades / result.total_trades

        except Exception as e:
            self.logger.error(f"计算性能指标失败: {str(e)}")

        return result

    def run_portfolio_backtest(self, etf_codes: List[str] = None) -> Dict[str, BacktestResult]:
        """
        运行投资组合回测

        Args:
            etf_codes: ETF代码列表，如果为None则使用配置中的所有ETF

        Returns:
            回测结果字典
        """
        if etf_codes is None:
            etf_codes = [config['etf_code'] for config in ETF_GRID_CONFIG.etf_universe]

        self.logger.info(f"开始投资组合回测，包含ETF: {etf_codes}")

        results = {}
        capital_per_etf = self.initial_capital / len(etf_codes)

        for etf_code in etf_codes:
            try:
                result = self.run_backtest(etf_code, capital=capital_per_etf)
                results[etf_code] = result

                # 打印简要结果
                self.logger.info(f"{etf_code}: 收益率 {result.total_return:.2%}, "
                               f"交易次数 {result.total_trades}, "
                               f"胜率 {result.win_rate:.2%}")

            except Exception as e:
                self.logger.error(f"回测失败 {etf_code}: {str(e)}")

        # 计算投资组合整体表现
        self._calculate_portfolio_performance(results)

        return results

    def _calculate_portfolio_performance(self, results: Dict[str, BacktestResult]):
        """计算投资组合整体表现"""
        if not results:
            return

        total_return = sum(r.total_return for r in results.values()) / len(results)
        total_trades = sum(r.total_trades for r in results.values())
        avg_win_rate = sum(r.win_rate for r in results.values()) / len(results)
        total_commission = sum(r.total_commission for r in results.values())

        self.logger.info("=" * 60)
        self.logger.info("投资组合回测结果汇总:")
        self.logger.info(f"平均总收益率: {total_return:.2%}")
        self.logger.info(f"总交易次数: {total_trades}")
        self.logger.info(f"平均胜率: {avg_win_rate:.2%}")
        self.logger.info(f"总手续费: {total_commission:.2f}")
        self.logger.info("=" * 60)

    def generate_report(self, results: Dict[str, BacktestResult], output_path: str = None) -> str:
        """
        生成回测报告

        Args:
            results: 回测结果
            output_path: 输出文件路径

        Returns:
            报告内容
        """
        report_lines = []
        report_lines.append("ETF网格交易策略回测报告")
        report_lines.append("=" * 50)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"回测期间: {BACKTEST_CONFIG.start_date} 至 {BACKTEST_CONFIG.end_date}")
        report_lines.append(f"初始资金: {self.initial_capital:,.2f}")
        report_lines.append("")

        for etf_code, result in results.items():
            report_lines.append(f"ETF: {etf_code}")
            report_lines.append("-" * 30)
            report_lines.append(f"总收益率: {result.total_return:.2%}")
            report_lines.append(f"年化收益率: {result.annual_return:.2%}")
            report_lines.append(f"最大回撤: {result.max_drawdown:.2%}")
            report_lines.append(f"夏普比率: {result.sharpe_ratio:.2f}")
            report_lines.append(f"胜率: {result.win_rate:.2%}")
            report_lines.append(f"交易次数: {result.total_trades}")
            report_lines.append(f"盈利交易: {result.profit_trades}")
            report_lines.append(f"亏损交易: {result.loss_trades}")
            report_lines.append(f"平均盈利: {result.avg_profit:.2f}")
            report_lines.append(f"平均亏损: {result.avg_loss:.2f}")
            report_lines.append(f"盈亏比: {result.profit_factor:.2f}")
            report_lines.append(f"总手续费: {result.total_commission:.2f}")
            report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.logger.info(f"回测报告已保存至: {output_path}")

        return report_content