# -*- coding: utf-8 -*-
"""
数据回退系统
当XtQuant连接失败时，提供高质量的模拟市场数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random
from .logger import get_logger

class DataFallbackSystem:
    """数据回退系统"""

    def __init__(self):
        self.logger = get_logger("DataFallbackSystem")
        self.fallback_active = False
        self.etf_base_prices = self._load_etf_configurations()
        self.volatility_profiles = self._create_volatility_profiles()

    def _load_etf_configurations(self) -> Dict[str, Dict]:
        """加载ETF配置信息"""
        from config.settings import ETF_GRID_CONFIG

        base_prices = {}
        for etf_config in ETF_GRID_CONFIG.etf_universe:
            etf_code = etf_config['etf_code']
            base_prices[etf_code] = {
                'base_price': etf_config['base_price'],
                'name': etf_config['etf_name'],
                'up_trigger': etf_config['up_trigger'],
                'down_trigger': etf_config['down_trigger']
            }

        self.logger.info(f"加载了 {len(base_prices)} 个ETF的基础配置")
        return base_prices

    def _create_volatility_profiles(self) -> Dict[str, float]:
        """创建不同ETF的波动率档案"""
        # 基于ETF类型设置不同的波动率
        volatility_profiles = {
            '159682': 0.025,  # 半导体ETF - 较高波动率
            '159380': 0.018,  # A500指数 - 中等波动率
            '159985': 0.022,  # 液晶ETF - 较高波动率
            '159937': 0.015,  # 平安9999 - 较低波动率
            '513730': 0.020,  # 通信ETF - 中等波动率
            '513130': 0.030,  # 纳斯达克 - 高波动率
        }

        return volatility_profiles

    def get_simulated_market_data(self,
                                symbols: List[str],
                                period: str = '1d',
                                count: int = 1,
                                fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取模拟市场数据

        Args:
            symbols: ETF代码列表
            period: 数据周期
            count: 数据条数
            fields: 需要的字段列表

        Returns:
            模拟的市场数据
        """
        if not self.fallback_active:
            self.fallback_active = True
            self.logger.warning("激活数据回退系统，使用模拟市场数据")

        if fields is None:
            fields = ['open', 'high', 'low', 'close', 'volume', 'amount']

        result = {}

        for symbol in symbols:
            etf_code = symbol.replace('.SZ', '').replace('.SH', '')
            data = self._generate_etf_data(symbol, etf_code, period, count, fields)
            result[symbol] = data

        return result

    def _generate_etf_data(self,
                          symbol: str,
                          etf_code: str,
                          period: str,
                          count: int,
                          fields: List[str]) -> Any:
        """为单个ETF生成模拟数据"""

        # 获取ETF基础配置
        if etf_code not in self.etf_base_prices:
            # 如果没有配置，使用默认值
            base_price = 1.0
            volatility = 0.02
            self.logger.warning(f"ETF {etf_code} 无配置，使用默认参数")
        else:
            config = self.etf_base_prices[etf_code]
            base_price = config['base_price']
            volatility = self.volatility_profiles.get(etf_code, 0.02)

        # 设置随机种子以确保一致性
        np.random.seed(hash(symbol) % 2**32)
        random.seed(hash(symbol) % 2**32)

        if count == 1:
            # 生成单日数据
            return self._generate_single_day_data(symbol, base_price, volatility, fields)
        else:
            # 生成多日数据
            return self._generate_multi_day_data(symbol, base_price, volatility, count, fields)

    def _generate_single_day_data(self,
                                symbol: str,
                                base_price: float,
                                volatility: float,
                                fields: List[str]) -> Any:
        """生成单日市场数据"""

        # 计算当日价格变动
        daily_return = np.random.normal(0, volatility)

        # 生成OHLC数据
        open_price = base_price * (1 + np.random.normal(0, volatility * 0.3))
        close_price = base_price * (1 + daily_return)

        # 确保价格逻辑关系
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility * 0.2)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility * 0.2)))

        # 生成成交量和成交额
        base_volume = np.random.normal(1000000, 200000)  # 基础成交量100万股
        volume = max(int(base_volume), 100000)  # 最小10万股
        amount = volume * close_price  # 成交额

        # 创建数据对象
        data_dict = {}
        if 'open' in fields:
            data_dict['open'] = round(open_price, 3)
        if 'high' in fields:
            data_dict['high'] = round(high_price, 3)
        if 'low' in fields:
            data_dict['low'] = round(low_price, 3)
        if 'close' in fields:
            data_dict['close'] = round(close_price, 3)
        if 'volume' in fields:
            data_dict['volume'] = volume
        if 'amount' in fields:
            data_dict['amount'] = round(amount, 2)

        # 返回类似pandas DataFrame的结构
        class SimulatedData:
            def __init__(self, data_dict):
                for key, value in data_dict.items():
                    setattr(self, key, value)

            def __getitem__(self, key):
                return getattr(self, key, None)

        return SimulatedData(data_dict)

    def _generate_multi_day_data(self,
                                symbol: str,
                                base_price: float,
                                volatility: float,
                                count: int,
                                fields: List[str]) -> pd.DataFrame:
        """生成多日市场数据"""

        dates = pd.date_range(end=datetime.now(), periods=count, freq='D')
        data = []

        current_price = base_price

        for i in range(count):
            # 生成每日价格变动
            daily_return = np.random.normal(0, volatility)

            # 生成OHLC数据
            open_price = current_price * (1 + np.random.normal(0, volatility * 0.3))
            close_price = current_price * (1 + daily_return)

            # 确保价格逻辑关系
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility * 0.2)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility * 0.2)))

            # 生成成交量
            base_volume = np.random.normal(1000000, 200000)
            volume = max(int(base_volume), 100000)
            amount = volume * close_price

            day_data = {
                'date': dates[i],
                'open': round(open_price, 3),
                'high': round(high_price, 3),
                'low': round(low_price, 3),
                'close': round(close_price, 3),
                'volume': volume,
                'amount': round(amount, 2)
            }

            # 只保留请求的字段
            filtered_data = {k: v for k, v in day_data.items() if k in fields or k == 'date'}
            data.append(filtered_data)

            # 更新当前价格
            current_price = close_price

        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)

        return df

    def get_simulated_local_data(self,
                                stock_list: List[str],
                                field_list: List[str],
                                period: str = '1d',
                                count: int = -1,
                                start_time: str = '',
                                end_time: str = '') -> Dict[str, Any]:
        """
        生成模拟历史数据用于本地数据回退

        Args:
            stock_list: 股票代码列表
            field_list: 字段列表
            period: 数据周期
            count: 数据条数
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            模拟历史数据字典
        """
        if not self.fallback_active:
            self.fallback_active = True
            self.logger.warning("本地数据回退系统激活，使用模拟历史数据")

        result = {}

        for symbol in stock_list:
            etf_code = symbol.replace('.SZ', '').replace('.SH', '')

            # 确定数据点数量
            data_count = self._calculate_data_count(count, start_time, end_time, period)

            # 生成历史数据
            historical_data = self._generate_historical_data(
                symbol, etf_code, field_list, period, data_count, start_time, end_time
            )

            result[symbol] = historical_data

        return result

    def _calculate_data_count(self, count: int, start_time: str, end_time: str, period: str) -> int:
        """计算合适的数据点数量"""
        if count > 0:
            return count

        # 对于count=-1，根据日期范围估算
        if start_time and end_time:
            trading_days = self._calculate_trading_days(start_time, end_time)
            if period == '1d':
                return trading_days
            elif period == '1w':
                return trading_days // 7
            elif period == '1m':
                return trading_days // 30
            elif period == '1h':
                return trading_days * 4  # 每天4小时

        # 默认回退值
        return 252  # 约1年的交易日

    def _calculate_trading_days(self, start_time: str, end_time: str) -> int:
        """计算交易日数量"""
        try:
            from datetime import datetime, timedelta
            import numpy as np

            # 尝试不同的日期格式
            for date_format in ['%Y%m%d', '%Y-%m-%d', '%Y%m%d%H%M%S']:
                try:
                    start_dt = datetime.strptime(start_time, date_format)
                    end_dt = datetime.strptime(end_time, date_format)
                    break
                except ValueError:
                    continue
            else:
                # 如果都失败，使用默认值
                return 252

            total_days = (end_dt - start_dt).days
            # 排除周末，约70%是交易日
            trading_days = int(total_days * 0.7)
            # 再排除节假日，约95%
            trading_days = int(trading_days * 0.95)

            return max(1, trading_days)

        except Exception:
            return 252

    def _generate_historical_data(self,
                                symbol: str,
                                etf_code: str,
                                field_list: List[str],
                                period: str,
                                count: int,
                                start_time: str,
                                end_time: str) -> pd.DataFrame:
        """生成历史数据"""
        # 获取ETF基础配置
        if etf_code not in self.etf_base_prices:
            base_price = 1.0
            volatility = 0.02
            self.logger.warning(f"ETF {etf_code} 无配置，使用默认参数")
        else:
            config = self.etf_base_prices[etf_code]
            base_price = config['base_price']
            volatility = self.volatility_profiles.get(etf_code, 0.02)

        # 设置随机种子以确保一致性
        np.random.seed(hash(symbol) % 2**32)

        # 生成日期序列
        dates = self._generate_date_series(count, period, start_time, end_time)

        # 生成价格数据
        current_price = base_price
        data = []

        for date in dates:
            # 生成每日价格变动
            if period in ['1d', '1w', '1m']:
                daily_return = np.random.normal(0, volatility)
            else:  # 小时级别
                daily_return = np.random.normal(0, volatility * 0.1)

            # 生成OHLC数据
            open_price = current_price * (1 + np.random.normal(0, volatility * 0.3))
            close_price = current_price * (1 + daily_return)

            # 确保价格逻辑关系
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility * 0.2)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility * 0.2)))

            # 生成成交量
            base_volume = np.random.normal(1000000, 200000)
            volume = max(int(base_volume), 100000)
            amount = volume * close_price

            day_data = {
                'date': date,
                'open': round(open_price, 3),
                'high': round(high_price, 3),
                'low': round(low_price, 3),
                'close': round(close_price, 3),
                'volume': volume,
                'amount': round(amount, 2)
            }

            # 只保留请求的字段
            filtered_data = {k: v for k, v in day_data.items() if k in field_list or k == 'date'}
            data.append(filtered_data)

            # 更新当前价格
            current_price = close_price

        df = pd.DataFrame(data)

        # 设置日期索引
        if 'date' in df.columns:
            df.set_index('date', inplace=True)

        return df

    def _generate_date_series(self, count: int, period: str, start_time: str, end_time: str) -> List:
        """生成日期序列"""
        from datetime import datetime, timedelta
        import pandas as pd

        try:
            # 如果有指定的时间范围，优先使用
            if start_time and end_time:
                for date_format in ['%Y%m%d', '%Y-%m-%d']:
                    try:
                        start_dt = datetime.strptime(start_time, date_format)
                        end_dt = datetime.strptime(end_time, date_format)
                        break
                    except ValueError:
                        continue

                # 根据周期生成日期
                if period == '1d':
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='B')  # 工作日
                elif period == '1w':
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='W')
                elif period == '1m':
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='M')
                elif period == '1h':
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='H')
                else:
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

                # 限制数量
                if len(dates) > count and count > 0:
                    dates = dates[-count:]
                elif count > 0:
                    dates = dates[:count]

                return dates.tolist()

            else:
                # 如果没有时间范围，从当前日期往前推
                end_dt = datetime.now()
                if period == '1d':
                    start_dt = end_dt - timedelta(days=count)
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='B')
                elif period == '1w':
                    start_dt = end_dt - timedelta(weeks=count)
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='W')
                elif period == '1m':
                    start_dt = end_dt - timedelta(days=count * 30)
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='M')
                else:
                    start_dt = end_dt - timedelta(days=count)
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

                return dates.tolist()

        except Exception as e:
            self.logger.warning(f"生成日期序列失败: {e}")
            # 回退到简单的时间序列
            end_dt = datetime.now()
            dates = [end_dt - timedelta(days=i) for i in range(count)]
            return dates[::-1]  # 反转使其按时间顺序

    def get_simulated_price(self, symbol: str) -> float:
        """获取单个ETF的模拟价格"""
        etf_code = symbol.replace('.SZ', '').replace('.SH', '')

        if etf_code not in self.etf_base_prices:
            return 1.0

        base_price = self.etf_base_prices[etf_code]['base_price']
        volatility = self.volatility_profiles.get(etf_code, 0.02)

        # 生成价格变动
        daily_return = np.random.normal(0, volatility)
        current_price = base_price * (1 + daily_return)

        return round(current_price, 3)

    def is_fallback_active(self) -> bool:
        """检查回退系统是否激活"""
        return self.fallback_active

    def get_system_status(self) -> Dict[str, Any]:
        """获取回退系统状态"""
        return {
            'fallback_active': self.fallback_active,
            'supported_etfs': list(self.etf_base_prices.keys()),
            'etf_count': len(self.etf_base_prices),
            'data_quality': 'simulated'
        }

# 全局回退系统实例
fallback_system = DataFallbackSystem()