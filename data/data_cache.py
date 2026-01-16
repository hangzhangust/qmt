# encoding:utf-8
"""
数据缓存模块
提供本地数据缓存功能，提高数据获取性能
"""
import os
import pickle
import pandas as pd
from typing import Tuple, Optional
from datetime import datetime, timedelta


class DataCache:
    """
    数据缓存管理器
    用于缓存历史行情数据，减少重复下载
    """

    def __init__(self, cache_dir: str = None, cache_expire_days: int = 7):
        """
        初始化数据缓存管理器

        参数:
            cache_dir: 缓存目录路径，默认为~/QMT_Strategy_Data/cache
            cache_expire_days: 缓存过期天数，默认7天
        """
        if cache_dir is None:
            home_dir = os.path.expanduser("~")
            cache_dir = os.path.join(home_dir, "QMT_Strategy_Data", "cache")

        self.cache_dir = cache_dir
        self.cache_expire_days = cache_expire_days

        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            print(f"创建缓存目录: {self.cache_dir}")

    def _get_cache_filename(self, stock_code: str, start_date: str, end_date: str, period: str = '1d') -> str:
        """
        生成缓存文件名

        参数:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期 (1d, 1w, 1m等)

        返回:
            str: 缓存文件路径
        """
        filename = f"{stock_code}_{period}_{start_date}_{end_date}.pkl"
        return os.path.join(self.cache_dir, filename)

    def _is_cache_fresh(self, cache_file: str) -> bool:
        """
        检查缓存是否新鲜

        参数:
            cache_file: 缓存文件路径

        返回:
            bool: 缓存是否在有效期内
        """
        if not os.path.exists(cache_file):
            return False

        # 获取文件修改时间
        file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        expire_time = datetime.now() - timedelta(days=self.cache_expire_days)

        return file_mtime > expire_time

    def get_cached_data(self, stock_code: str, start_date: str, end_date: str, period: str = '1d') -> Tuple[Optional[pd.DataFrame], bool]:
        """
        从缓存获取数据

        参数:
            stock_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期 (1d, 1w, 1m等)

        返回:
            tuple: (DataFrame数据对象, 是否来自缓存)
                  如果缓存不存在或已过期，返回 (None, False)
        """
        cache_file = self._get_cache_filename(stock_code, start_date, end_date, period)

        if os.path.exists(cache_file):
            # 检查缓存是否新鲜
            if self._is_cache_fresh(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    print(f"从缓存加载数据: {stock_code} ({start_date} - {end_date})")
                    return data, True
                except Exception as e:
                    print(f"读取缓存文件失败: {e}")
            else:
                print(f"缓存已过期: {cache_file}")

        return None, False

    def save_to_cache(self, stock_code: str, data: pd.DataFrame, start_date: str, end_date: str, period: str = '1d') -> None:
        """
        保存数据到缓存

        参数:
            stock_code: 股票代码
            data: 要缓存的数据
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期 (1d, 1w, 1m等)
        """
        cache_file = self._get_cache_filename(stock_code, start_date, end_date, period)

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            print(f"数据已缓存: {stock_code} ({start_date} - {end_date})")
        except Exception as e:
            print(f"保存缓存失败: {e}")

    def clear_cache(self, stock_code: str = None, older_than_days: int = None) -> None:
        """
        清理缓存

        参数:
            stock_code: 指定股票代码，如果为None则清理所有
            older_than_days: 清理多少天前的缓存，如果为None则清理所有
        """
        if not os.path.exists(self.cache_dir):
            return

        try:
            for filename in os.listdir(self.cache_dir):
                if stock_code and not filename.startswith(stock_code):
                    continue

                file_path = os.path.join(self.cache_dir, filename)

                # 检查文件年龄
                if older_than_days is not None:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    expire_time = datetime.now() - timedelta(days=older_than_days)
                    if file_mtime > expire_time:
                        continue

                os.remove(file_path)
                print(f"删除缓存文件: {filename}")

        except Exception as e:
            print(f"清理缓存失败: {e}")

    def get_cache_info(self) -> dict:
        """
        获取缓存信息

        返回:
            dict: 缓存统计信息
        """
        if not os.path.exists(self.cache_dir):
            return {
                'cache_dir': self.cache_dir,
                'file_count': 0,
                'total_size_mb': 0
            }

        file_count = 0
        total_size = 0

        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
        except Exception as e:
            print(f"获取缓存信息失败: {e}")

        return {
            'cache_dir': self.cache_dir,
            'file_count': file_count,
            'total_size_mb': round(total_size / 1024 / 1024, 2)
        }
