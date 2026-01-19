# encoding:utf-8
"""
XtQuant数据接口模块
封装xtdata模块，提供统一的数据获取接口
"""
import pandas as pd
from typing import List, Optional
from xtquant import xtdata
from .data_cache import DataCache


class XtDataFeed:
    """
    XtQuant数据源封装
    提供市场数据获取功能，支持缓存
    """

    def __init__(self, use_cache: bool = True, cache_dir: str = None, cache_expire_days: int = 7):
        """
        初始化XtQuant数据源

        参数:
            use_cache: 是否使用缓存
            cache_dir: 缓存目录
            cache_expire_days: 缓存过期天数
        """
        self.use_cache = use_cache
        if self.use_cache:
            self.cache = DataCache(cache_dir=cache_dir, cache_expire_days=cache_expire_days)
        else:
            self.cache = None

    def get_market_data(self, field_list: List[str], stock_list: List[str],
                       period: str = '1d', count: int = 1, start_time: str = '',
                       end_time: str = '', dividend_type: str = 'none',
                       fill_data: bool = True) -> dict:
        """
        获取市场数据（实时或历史）

        参数:
            field_list: 字段列表，如 ['open', 'high', 'low', 'close', 'volume']
            stock_list: 股票代码列表，如 ['000001.SZ', '600000.SH']
            period: 周期，如 '1d', '1w', '1m', '1tick', '1min'
            count: 数据条数，-1表示全部
            start_time: 开始时间 (YYYYMMDD或YYYYMMDD HHMMSS格式)
            end_time: 结束时间 (YYYYMMDD或YYYYMMDD HHMMSS格式)
            dividend_type: 除权类型，'none'/'front'/'follow'/'back'/'front_follow' (ETFs use 'none')
            fill_data: 是否填充数据

        返回:
            dict: {stock_code: DataFrame}
        """
        try:
            data = xtdata.get_market_data_ex(
                field_list=field_list,
                stock_list=stock_list,
                period=period,
                count=count,
                start_time=start_time,
                end_time=end_time,
                dividend_type=dividend_type,
                fill_data=fill_data
            )
            return data

        except Exception as e:
            print(f"获取市场数据失败: {e}")
            return {}

    def download_history_data(self, stock_code: str, period: str,
                             start_time: str, end_time: str = '') -> bool:
        """
        下载历史数据到本地

        参数:
            stock_code: 股票代码
            period: 周期 ('tick', '1d', '1w', '1m')
            start_time: 开始时间 (YYYYMMDD或YYYYMMDD HHMMSS格式)
            end_time: 结束时间 (可选)

        返回:
            bool: 是否成功
        """
        try:
            xtdata.download_history_data(stock_code, period, start_time, end_time)
            print(f"下载历史数据成功: {stock_code} ({start_time} - {end_time})")
            return True

        except Exception as e:
            print(f"下载历史数据失败: {e}")
            return False

    def get_history_data(self, stock_code: str, field_list: List[str],
                        start_date: str, end_date: str, period: str = '1d',
                        use_cache: bool = None) -> Optional[pd.DataFrame]:
        """
        获取历史数据（带缓存支持）

        参数:
            stock_code: 股票代码
            field_list: 字段列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期
            use_cache: 是否使用缓存，默认使用初始化时的设置

        返回:
            DataFrame: 历史数据，如果失败返回None
        """
        import time
        from datetime import datetime, timedelta

        # 决定是否使用缓存
        should_use_cache = use_cache if use_cache is not None else self.use_cache

        # 尝试从缓存获取
        if should_use_cache and self.cache:
            data, from_cache = self.cache.get_cached_data(stock_code, start_date, end_date, period)
            if data is not None:
                return data

        # Check if date range is more than 2 years - use chunked download
        try:
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            date_range_days = (end_dt - start_dt).days

            # Use chunked download for ranges longer than 2 years
            if date_range_days > 730:  # 2 years
                print(f"长时间范围数据下载（{date_range_days // 365}年），使用分块下载: {stock_code}")
                return self._get_history_data_chunked(
                    stock_code, field_list, start_date, end_date, period, should_use_cache
                )
        except Exception as e:
            print(f"日期范围检查失败，使用常规下载: {e}")

        # 常规下载历史数据
        success = self.download_history_data(stock_code, period, start_date, end_date)
        if not success:
            return None

        # Wait a moment for download to complete
        time.sleep(0.5)

        # 获取数据 - Try multiple times
        max_retries = 3
        for retry in range(max_retries):
            try:
                # ETFs don't support dividend adjustment, use 'none'
                # 股票代码以.SH或.SZ结尾的ETF不支持除权，使用'none'
                dividend_type = 'none'

                data_dict = xtdata.get_market_data_ex(
                    field_list=field_list,
                    stock_list=[stock_code],
                    period=period,
                    start_time=start_date,
                    end_time=end_date,
                    dividend_type=dividend_type,
                    fill_data=True
                )

                # Check if data_dict is None
                if data_dict is None:
                    if retry < max_retries - 1:
                        print(f"数据未准备好，重试 {retry + 1}/{max_retries}: {stock_code}")
                        time.sleep(1)
                        continue
                    else:
                        print(f"获取数据失败（返回None）: {stock_code}")
                        return None

                # Check if stock_code exists in dict
                if stock_code not in data_dict or data_dict[stock_code] is None:
                    print(f"获取数据失败（无数据）: {stock_code}")
                    return None

                data = data_dict[stock_code]

                # 保存到缓存
                if should_use_cache and self.cache:
                    self.cache.save_to_cache(stock_code, data, start_date, end_date, period)

                return data

            except Exception as e:
                if retry < max_retries - 1:
                    print(f"获取历史数据异常，重试 {retry + 1}/{max_retries}: {e}")
                    time.sleep(1)
                    continue
                else:
                    print(f"获取历史数据失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return None

        return None

    def _get_history_data_chunked(self, stock_code: str, field_list: List[str],
                                  start_date: str, end_date: str, period: str = '1d',
                                  use_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        分块获取长时间范围的历史数据

        参数:
            stock_code: 股票代码
            field_list: 字段列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期
            use_cache: 是否使用缓存

        返回:
            DataFrame: 合并后的历史数据
        """
        import time
        from datetime import datetime, timedelta

        try:
            all_data = []
            current_start = datetime.strptime(start_date, '%Y%m%d')
            final_end = datetime.strptime(end_date, '%Y%m%d')

            # Split into 1-year chunks
            chunk_years = 1
            chunk_days = chunk_years * 365

            chunk_num = 0
            while current_start < final_end:
                chunk_num += 1
                current_end = min(current_start + timedelta(days=chunk_days), final_end)

                chunk_start_str = current_start.strftime('%Y%m%d')
                chunk_end_str = current_end.strftime('%Y%m%d')

                print(f"  下载第 {chunk_num} 块: {chunk_start_str} - {chunk_end_str}")

                # Download this chunk
                success = self.download_history_data(stock_code, period, chunk_start_str, chunk_end_str)
                if not success:
                    print(f"  警告: 第 {chunk_num} 块下载失败，跳过")
                    current_start = current_end
                    continue

                # Wait for download
                time.sleep(0.5)

                # Get data with retries
                max_retries = 3
                chunk_data = None
                for retry in range(max_retries):
                    try:
                        data_dict = xtdata.get_market_data_ex(
                            field_list=field_list,
                            stock_list=[stock_code],
                            period=period,
                            start_time=chunk_start_str,
                            end_time=chunk_end_str,
                            dividend_type='none',
                            fill_data=True
                        )

                        if data_dict is not None and stock_code in data_dict and data_dict[stock_code] is not None:
                            chunk_data = data_dict[stock_code]
                            break
                        else:
                            if retry < max_retries - 1:
                                print(f"  第 {chunk_num} 块数据未准备好，重试 {retry + 1}/{max_retries}")
                                time.sleep(1)
                            else:
                                print(f"  警告: 第 {chunk_num} 块无数据（可能该时间段ETF未上市）")

                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"  第 {chunk_num} 块获取异常，重试 {retry + 1}/{max_retries}: {e}")
                            time.sleep(1)
                        else:
                            print(f"  警告: 第 {chunk_num} 块获取失败: {e}")

                # If we got data, add it to our collection
                if chunk_data is not None and not chunk_data.empty:
                    all_data.append(chunk_data)

                # Move to next chunk
                current_start = current_end + timedelta(days=1)

            # Combine all chunks
            if all_data:
                print(f"  合并 {len(all_data)} 个数据块")
                combined_data = pd.concat(all_data, axis=0)

                # Remove duplicates (in case of overlap)
                combined_data = combined_data[~combined_data.index.duplicated(keep='first')]

                # Sort by date
                combined_data = combined_data.sort_index()

                # Save to cache
                if use_cache and self.cache:
                    self.cache.save_to_cache(stock_code, combined_data, start_date, end_date, period)

                print(f"  获取数据成功: {len(combined_data)} 条记录")
                return combined_data
            else:
                print(f"  错误: 未获取到任何数据")
                return None

        except Exception as e:
            print(f"分块下载失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_instrument_info(self, stock_code: str) -> dict:
        """
        获取合约信息

        参数:
            stock_code: 股票代码

        返回:
            dict: 合约信息
        """
        try:
            info = xtdata.get_instrument_info(stock_code)
            return info

        except Exception as e:
            print(f"获取合约信息失败: {e}")
            return {}

    def get_trading_dates(self, start_date: str, end_date: str, market: str = 'SH') -> List[str]:
        """
        获取交易日历

        参数:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            market: 市场 ('SH', 'SZ')

        返回:
            list: 交易日期列表
        """
        try:
            dates = xtdata.get_trading_dates(start_date, end_date, market)
            return dates

        except Exception as e:
            print(f"获取交易日历失败: {e}")
            return []

    def connect(self) -> bool:
        """
        连接MiniQMT数据服务

        返回:
            bool: 是否连接成功
        """
        try:
            # xtdata会自动连接，这里只是测试连接
            result = xtdata.get_full_tick(['000001.SZ'])
            return result is not None

        except Exception as e:
            print(f"连接MiniQMT数据服务失败: {e}")
            return False

    def get_earliest_date(self, stock_code: str,
                         start_date: str = None, end_date: str = None) -> Optional[str]:
        """
        获取股票/ETF在指定时间段内的最早可用日期

        参数:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)，如果为None则使用2000年1月1日
            end_date: 结束日期 (YYYYMMDD)，如果为None则使用当前日期

        返回:
            str: 最早日期，格式YYYYMMDD，如果无法确定则返回None
        """
        try:
            from datetime import datetime, timedelta

            # 如果没有指定日期范围，使用一个很大的范围来检测上市日期
            if start_date is None:
                start_date = '20000101'  # 从2000年开始检查
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')

            # 使用分块下载来获取长期数据
            data = self.get_history_data(
                stock_code=stock_code,
                field_list=['close'],
                start_date=start_date,
                end_date=end_date,
                period='1d',
                use_cache=True  # 使用缓存以加快速度
            )

            if data is not None and not data.empty:
                # 找到第一个非NaN的数据点
                valid_data = data[data['close'].notna() & (data['close'] > 0)]
                if not valid_data.empty:
                    first_date = valid_data.index[0]
                    if isinstance(first_date, str):
                        # Already a string, just format it
                        return first_date.replace('-', '')
                    else:
                        # It's a datetime object, format it
                        return first_date.strftime('%Y%m%d')

        except Exception as e:
            print(f"无法获取 {stock_code} 的最早日期: {e}")

        return None

    @staticmethod
    def format_date(date_str: str, input_format: str = '%Y%m%d', output_format: str = '%Y-%m-%d') -> str:
        """
        格式化日期字符串

        参数:
            date_str: 日期字符串
            input_format: 输入格式
            output_format: 输出格式

        返回:
            str: 格式化后的日期字符串
        """
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, input_format)
            return dt.strftime(output_format)
        except:
            return date_str
