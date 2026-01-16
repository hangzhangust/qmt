# encoding:utf-8
"""
Backtrader回测引擎模块
提供回测引擎和自定义数据源
"""
import backtrader as bt
import pandas as pd
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
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
            print(f"\n夏普比率: {sharpe.get('sharperatio', 0):.4f}")

        # 年化收益率
        if 'annual_return' in results and results['annual_return']:
            ar = results['annual_return']
            print(f"\n年化收益率:")
            for year, ret in ar.items():
                if isinstance(year, int):
                    print(f"  {year}: {ret:.2%}")

        print("=" * 80 + "\n")
