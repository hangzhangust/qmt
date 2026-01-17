# encoding:utf-8
"""
Backtrader回测引擎模块
提供回测引擎和自定义数据源
"""
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import numpy as np
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.xtdata_feed import XtDataFeed


class XtDataPandasFeed(bt.feeds.PandasData):
    """
    基于XtQuant数据的Backtrader数据源
    """
    params = (
        ('datetime', None),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None),
    )

    @classmethod
    def from_xtdata(cls, stock_code: str, start_date: str, end_date: str,
                    period: str = '1d', use_cache: bool = True):
        """
        从XtQuant创建数据源

        参数:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期
            use_cache: 是否使用缓存

        返回:
            XtDataPandasFeed: Backtrader数据源实例
        """
        # 创建XtQuant数据接口
        xt_feed = XtDataFeed(use_cache=use_cache)

        # 获取历史数据
        field_list = ['open', 'high', 'low', 'close', 'volume', 'amount']
        data = xt_feed.get_history_data(
            stock_code=stock_code,
            field_list=field_list,
            start_date=start_date,
            end_date=end_date,
            period=period,
            use_cache=use_cache
        )

        if data is None or data.empty:
            raise ValueError(f"无法获取数据: {stock_code} ({start_date} - {end_date})")

        # 数据预处理
        data = cls._preprocess_data(data)

        # 创建数据源
        return cls(dataname=data, name=stock_code)

    @staticmethod
    def _preprocess_data(data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理数据

        参数:
            data: 原始数据

        返回:
            DataFrame: 处理后的数据
        """
        # 确保索引是datetime类型
        if not isinstance(data.index, pd.DatetimeIndex):
            try:
                data.index = pd.to_datetime(data.index)
            except:
                pass

        # 确保必需的列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"缺少必需的列: {col}")

        # 去除NaN值
        data = data.dropna(subset=required_columns)

        # 排序
        data = data.sort_index()

        return data

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, stock_code: str):
        """
        从DataFrame创建数据源

        参数:
            df: 数据DataFrame
            stock_code: 股票代码

        返回:
            XtDataPandasFeed: Backtrader数据源实例
        """
        # 数据预处理
        data = cls._preprocess_data(df)

        # 创建数据源
        return cls(dataname=data, name=stock_code)


class BacktestEngine:
    """
    Backtrader回测引擎
    封装Cerebro，提供简洁的回测接口
    """

    def __init__(self, initial_cash: float = 1000000.0, commission: float = 0.0001):
        """
        初始化回测引擎

        参数:
            initial_cash: 初始资金
            commission: 手续费率 (默认0.01%)
        """
        self.cerebro = bt.Cerebro()

        # 设置初始资金
        self.cerebro.broker.setcash(initial_cash)

        # 设置手续费
        self.cerebro.broker.setcommission(commission=commission)

        # 数据源列表
        self.data_feeds = []

        # 分析器列表
        self.analyzers = {}

    def add_data_feeds(self, stock_codes: List[str], start_date: str, end_date: str,
                      period: str = '1d', use_cache: bool = True) -> None:
        """
        批量添加数据源

        参数:
            stock_codes: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期
            use_cache: 是否使用缓存
        """
        for stock_code in stock_codes:
            try:
                data_feed = XtDataPandasFeed.from_xtdata(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date,
                    period=period,
                    use_cache=use_cache
                )
                self.cerebro.adddata(data_feed, name=stock_code)
                self.data_feeds.append(stock_code)
                print(f"添加数据源: {stock_code}")
            except Exception as e:
                print(f"添加数据源失败 {stock_code}: {e}")

    def add_strategy(self, strategy_class, **kwargs) -> None:
        """
        添加策略

        参数:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **kwargs)

    def add_analyzers(self) -> None:
        """
        添加标准分析器
        """
        # 夏普比率
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days)

        # 最大回撤
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        # 收益率
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

        # 年化收益率
        self.cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')

        # 交易统计
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    def set_cerebro_params(self, **kwargs) -> None:
        """
        设置Cerebro参数

        参数:
            **kwargs: Cerebro参数
        """
        for key, value in kwargs.items():
            setattr(self.cerebro, key, value)

    def run(self) -> List[bt.Strategy]:
        """
        运行回测

        返回:
            list: 策略实例列表
        """
        print("=" * 80)
        print("开始回测...")
        print("=" * 80)

        # 运行回测
        strategies = self.cerebro.run()

        print("=" * 80)
        print("回测完成")
        print("=" * 80)

        return strategies

    def get_results(self, strategy: bt.Strategy) -> Dict[str, Any]:
        """
        获取回测结果

        参数:
            strategy: 策略实例

        返回:
            dict: 回测结果
        """
        results = {}

        # 获取分析器结果
        if hasattr(strategy, 'analyzers'):
            # 夏普比率
            if hasattr(strategy.analyzers, 'sharpe'):
                results['sharpe_ratio'] = strategy.analyzers.sharpe.get_analysis()

            # 最大回撤
            if hasattr(strategy.analyzers, 'drawdown'):
                results['drawdown'] = strategy.analyzers.drawdown.get_analysis()

            # 收益率
            if hasattr(strategy.analyzers, 'returns'):
                results['returns'] = strategy.analyzers.returns.get_analysis()

            # 年化收益率
            if hasattr(strategy.analyzers, 'annual_return'):
                results['annual_return'] = strategy.analyzers.annual_return.get_analysis()

            # 交易统计
            if hasattr(strategy.analyzers, 'trades'):
                results['trades'] = strategy.analyzers.trades.get_analysis()

        # 获取最终资金和收益
        results['final_value'] = strategy.broker.getvalue()
        results['start_value'] = self.cerebro.broker.startingcash
        results['total_return'] = (results['final_value'] - results['start_value']) / results['start_value']

        return results

    def print_results(self, strategy: bt.Strategy) -> None:
        """
        打印回测结果

        参数:
            strategy: 策略实例
        """
        results = self.get_results(strategy)

        print("\n" + "=" * 80)
        print("回测结果")
        print("=" * 80)

        # 资金信息
        print(f"初始资金: {results['start_value']:,.2f}")
        print(f"最终资金: {results['final_value']:,.2f}")
        print(f"总收益率: {results['total_return']*100:.2f}%")

        # 最大回撤
        if 'drawdown' in results and results['drawdown']:
            dd = results['drawdown']
            print(f"\n最大回撤: {dd.get('max', {}).get('drawdown', 0):.2f}%")
            print(f"最大回撤持续天数: {dd.get('max', {}).get('len', 0)}")

        # 夏普比率
        if 'sharpe_ratio' in results and results['sharpe_ratio']:
            sharpe = results['sharpe_ratio']
            sharpe_value = sharpe.get('sharperatio') or 0
            print(f"\n夏普比率: {sharpe_value:.4f}")

        # 年化收益率
        if 'annual_return' in results and results['annual_return']:
            ar = results['annual_return']
            print(f"\n年化收益率:")
            for year, ret in ar.items():
                if isinstance(year, int):
                    print(f"  {year}: {ret:.2%}")

        print("=" * 80 + "\n")

    def calculate_enhanced_metrics(self, strategy: bt.Strategy) -> Dict[str, Any]:
        """
        计算增强的性能指标

        参数:
            strategy: 策略实例

        返回:
            dict: 增强的性能指标
        """
        results = self.get_results(strategy)
        enhanced = {}

        # 基础指标
        enhanced['total_return'] = results['total_return']
        enhanced['final_value'] = results['final_value']
        enhanced['start_value'] = results['start_value']

        # 最大回撤
        if 'drawdown' in results and results['drawdown']:
            dd = results['drawdown']
            enhanced['max_drawdown'] = dd.get('max', {}).get('drawdown', 0)
            enhanced['max_drawdown_len'] = dd.get('max', {}).get('len', 0)
        else:
            enhanced['max_drawdown'] = 0
            enhanced['max_drawdown_len'] = 0

        # 夏普比率
        if 'sharpe_ratio' in results and results['sharpe_ratio']:
            enhanced['sharpe_ratio'] = results['sharpe_ratio'].get('sharperatio', 0)
        else:
            enhanced['sharpe_ratio'] = 0

        # 年化收益率（从年化收益率分析器计算平均）
        if 'annual_return' in results and results['annual_return']:
            ar_list = [v for k, v in results['annual_return'].items() if isinstance(k, int)]
            if ar_list:
                enhanced['avg_annual_return'] = np.mean(ar_list)
            else:
                enhanced['avg_annual_return'] = 0
        else:
            enhanced['avg_annual_return'] = 0

        # 计算波动率（从日收益率）
        if 'returns' in results and results['returns']:
            rets = results['returns']
            if isinstance(rets, dict) and 'rnorm100' in rets:
                # 使用backtrader计算的年化收益率标准差
                enhanced['volatility'] = abs(rets.get('rnorm100', 0))
            else:
                enhanced['volatility'] = 0
        else:
            enhanced['volatility'] = 0

        # Sortino比率（简化计算：夏普比率 * sqrt(2) 作为近似）
        # 实际应使用下行波动率计算
        if enhanced['volatility'] > 0:
            enhanced['sortino_ratio'] = enhanced['sharpe_ratio'] * 1.414
        else:
            enhanced['sortino_ratio'] = 0

        # 交易统计
        if 'trades' in results and results['trades']:
            trades = results['trades']
            enhanced['total_trades'] = trades.get('total', {}).get('total', 0)
            enhanced['won_trades'] = trades.get('won', {}).get('total', 0)
            enhanced['lost_trades'] = trades.get('lost', {}).get('total', 0)
            if enhanced['total_trades'] > 0:
                enhanced['win_rate'] = enhanced['won_trades'] / enhanced['total_trades']
            else:
                enhanced['win_rate'] = 0
        else:
            enhanced['total_trades'] = 0
            enhanced['won_trades'] = 0
            enhanced['lost_trades'] = 0
            enhanced['win_rate'] = 0

        return enhanced

    def plot_results(self, strategy: bt.Strategy, save_path: str = None,
                    show: bool = True, figsize: tuple = (16, 10)) -> None:
        """
        绘制回测结果图表（2x2子图）

        参数:
            strategy: 策略实例
            save_path: 保存路径（可选）
            show: 是否显示图表
            figsize: 图表大小
        """
        # 创建2x2子图
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        fig.suptitle('All-Weather Strategy Backtest Results', fontsize=16, fontweight='bold')

        # 绘制4个子图
        self._plot_equity_curve(strategy, axes[0, 0])
        self._plot_drawdown(strategy, axes[0, 1])
        self._plot_returns_distribution(strategy, axes[1, 0])
        self._plot_asset_allocation(strategy, axes[1, 1])

        # 调整布局
        plt.tight_layout()

        # 保存图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"[BacktestEngine] 图表已保存: {save_path}")

        # 显示图表
        if show:
            plt.show()
        else:
            plt.close()

    def _plot_equity_curve(self, strategy: bt.Strategy, ax) -> None:
        """
        绘制资金曲线

        参数:
            strategy: 策略实例
            ax: matplotlib子图轴对象
        """
        # 获取历史资金数据
        values = []  # 资金值
        dates = []   # 日期

        # 从策略的broker获取历史资金
        # 注意：需要策略在运行时记录资金历史
        if hasattr(strategy, 'value_history') and strategy.value_history:
            for date, value in strategy.value_history:
                dates.append(date)
                values.append(value)
        else:
            # 如果策略没有记录历史，使用当前值
            dates.append(datetime.now())
            values.append(strategy.broker.getvalue())

        if len(dates) > 1:
            # 计算累计收益率
            start_value = values[0]
            returns = [(v - start_value) / start_value * 100 for v in values]

            ax.plot(dates, returns, linewidth=2, color='#2E86AB', label='Cumulative Returns')
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)

            ax.set_title('Equity Curve', fontsize=12, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Returns (%)')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')

            # 格式化x轴日期
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        else:
            ax.text(0.5, 0.5, 'Insufficient data for equity curve',
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Equity Curve', fontsize=12, fontweight='bold')

    def _plot_drawdown(self, strategy: bt.Strategy, ax) -> None:
        """
        绘制回撤图

        参数:
            strategy: 策略实例
            ax: matplotlib子图轴对象
        """
        # 从分析器获取回撤数据
        results = self.get_results(strategy)

        if 'drawdown' in results and results['drawdown']:
            # 获取历史回撤数据（如果策略记录了）
            if hasattr(strategy, 'drawdown_history') and strategy.drawdown_history:
                dates = [d[0] for d in strategy.drawdown_history]
                drawdowns = [d[1] for d in strategy.drawdown_history]

                ax.fill_between(dates, 0, drawdowns, alpha=0.3, color='#A23B72')
                ax.plot(dates, drawdowns, linewidth=1.5, color='#A23B72', label='Drawdown')

                ax.set_title('Drawdown', fontsize=12, fontweight='bold')
                ax.set_xlabel('Date')
                ax.set_ylabel('Drawdown (%)')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='lower left')

                # 格式化x轴日期
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            else:
                # 显示最大回撤值
                max_dd = results['drawdown'].get('max', {}).get('drawdown', 0)
                ax.text(0.5, 0.5, f'Max Drawdown: {max_dd:.2f}%',
                       ha='center', va='center', fontsize=14,
                       transform=ax.transAxes, color='#A23B72')
                ax.set_title('Drawdown', fontsize=12, fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No drawdown data available',
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title('Drawdown', fontsize=12, fontweight='bold')

    def _plot_returns_distribution(self, strategy: bt.Strategy, ax) -> None:
        """
        绘制收益率分布直方图

        参数:
            strategy: 策略实例
            ax: matplotlib子图轴对象
        """
        # 获取日收益率数据
        if hasattr(strategy, 'returns_history') and strategy.returns_history:
            returns = strategy.returns_history

            # 绘制直方图
            n, bins, patches = ax.hist(returns, bins=30, alpha=0.7,
                                       color='#18A558', edgecolor='black')

            # 添加平均线
            mean_return = np.mean(returns)
            ax.axvline(mean_return, color='red', linestyle='--',
                      linewidth=2, label=f'Mean: {mean_return:.2f}%')

            ax.set_title('Returns Distribution', fontsize=12, fontweight='bold')
            ax.set_xlabel('Daily Returns (%)')
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3, axis='y')
            ax.legend(loc='upper right')
        else:
            # 计算简单收益率分布（基于总收益率）
            results = self.get_results(strategy)
            total_return = results['total_return'] * 100

            # 显示总收益率
            ax.text(0.5, 0.5, f'Total Return: {total_return:.2f}%',
                   ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, color='#18A558')
            ax.set_title('Returns Distribution', fontsize=12, fontweight='bold')

    def _plot_asset_allocation(self, strategy: bt.Strategy, ax) -> None:
        """
        绘制资产配置饼图

        参数:
            strategy: 策略实例
            ax: matplotlib子图轴对象
        """
        # 获取最终持仓
        if hasattr(strategy, 'get_final_allocation'):
            allocations = strategy.get_final_allocation()

            if allocations:
                # 准备数据
                labels = list(allocations.keys())
                sizes = list(allocations.values())
                colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E',
                         '#BC4B51', '#8367C7', '#5B8C85', '#E4B363', '#8D99AE']

                # 绘制饼图
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors[:len(labels)],
                                                  autopct='%1.1f%%', startangle=90)

                # 美化文本
                for text in texts:
                    text.set_fontsize(9)
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(8)
                    autotext.set_fontweight('bold')

                ax.set_title('Asset Allocation', fontsize=12, fontweight='bold')
            else:
                ax.text(0.5, 0.5, 'No allocation data available',
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Asset Allocation', fontsize=12, fontweight='bold')
        else:
            # 尝试从broker获取持仓数据
            total_value = strategy.broker.getvalue()
            cash = strategy.broker.getcash()
            positions_value = total_value - cash

            if positions_value > 0:
                labels = ['Cash', 'Positions']
                sizes = [cash, positions_value]
                colors = ['#6A994E', '#2E86AB']

                ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax.set_title('Asset Allocation', fontsize=12, fontweight='bold')
            else:
                ax.text(0.5, 0.5, f'Cash: {cash:,.0f}',
                       ha='center', va='center', fontsize=12,
                       transform=ax.transAxes)
                ax.set_title('Asset Allocation', fontsize=12, fontweight='bold')
