"""
回测服务层 - 处理回测业务逻辑
"""
import sys
import os
import asyncio
from datetime import datetime
from typing import Dict, Any
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backtesting.grid_batch_runner import GridBatchRunner


class BacktestService:
    """回测服务 - 封装回测引擎"""

    @staticmethod
    def generate_task_id() -> str:
        """生成任务ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"bt_{timestamp}"

    @staticmethod
    async def run_backtest(
        task_id: str,
        strategy_type: str,
        strategy_config: Dict[str, Any],
        backtest_config: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        运行回测任务（异步包装）

        Args:
            task_id: 任务ID
            strategy_type: 策略类型 ('grid', 'all_weather')
            strategy_config: 策略配置
            backtest_config: 回测配置
            progress_callback: 进度回调函数

        Returns:
            回测结果字典
        """
        try:
            # 报告开始
            if progress_callback:
                await progress_callback(10, "初始化回测引擎...")

            # 在线程池中运行同步回测
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                BacktestService._run_backtest_sync,
                task_id,
                strategy_type,
                strategy_config,
                backtest_config,
                progress_callback
            )

            return result

        except Exception as e:
            import traceback
            error_msg = f"回测失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[BacktestService] Error: {error_msg}")

            return {
                'error': error_msg,
                'task_id': task_id,
                'final_value': backtest_config.get('initial_cash', 1000000),
                'total_return': 0.0,
                'grid_triggers': [],
            }

    @staticmethod
    def _run_backtest_sync(
        task_id: str,
        strategy_type: str,
        strategy_config: Dict[str, Any],
        backtest_config: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        同步运行回测（在线程池中执行）

        Args:
            task_id: 任务ID
            strategy_type: 策略类型
            strategy_config: 策略配置
            backtest_config: 回测配置
            progress_callback: 进度回调（需要用asyncio包装）

        Returns:
            回测结果字典
        """
        try:
            # 提取回测参数
            start_date = backtest_config.get('start_date', '20240101')
            end_date = backtest_config.get('end_date', '20260121')
            initial_cash = backtest_config.get('initial_cash', 1000000)

            # 创建批量回测引擎
            runner = GridBatchRunner(
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash
            )

            # 根据策略类型执行回测
            if strategy_type == 'grid':
                # 网格交易策略
                result = BacktestService._run_grid_backtest(
                    runner, strategy_config, progress_callback
                )
            elif strategy_type == 'all_weather':
                # 全天候策略（待实现）
                result = BacktestService._run_all_weather_backtest(
                    runner, strategy_config, progress_callback
                )
            else:
                raise ValueError(f"不支持的策略类型: {strategy_type}")

            # 添加任务ID
            result['task_id'] = task_id

            return result

        except Exception as e:
            import traceback
            error_msg = f"回测执行失败: {str(e)}\n{traceback.format_exc()}"
            print(f"[BacktestService] Sync error: {error_msg}")

            return {
                'error': error_msg,
                'task_id': task_id,
                'final_value': backtest_config.get('initial_cash', 1000000),
                'total_return': 0.0,
                'grid_triggers': [],
            }

    @staticmethod
    def _run_grid_backtest(
        runner: GridBatchRunner,
        config: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """运行网格策略回测"""
        # 辅助函数：处理async回调
        def call_callback(progress, message):
            if progress_callback:
                try:
                    # 尝试直接调用（同步回调）
                    progress_callback(progress, message)
                except TypeError:
                    # 如果是coroutine，需要在事件循环中运行
                    try:
                        loop = asyncio.get_running_loop()
                        # 如果已经在事件循环中，创建任务
                        asyncio.create_task(progress_callback(progress, message))
                    except RuntimeError:
                        # 没有运行的事件循环，创建一个新的
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(progress_callback(progress, message))
                        loop.close()

        # 报告进度
        call_callback(30, "加载市场数据...")

        # 构建完整的策略配置
        full_config = {
            'etf_code': config.get('etf_code', ''),
            'etf_name': config.get('etf_name', config.get('etf_code', '')),
            'base_price': config.get('base_price', 1.0),
            'grid_spacing_up': config.get('grid_spacing_up', 5.0),
            'grid_spacing_down': config.get('grid_spacing_down', -5.0),
            'buy_amount': config.get('buy_amount', 10000),
            'sell_amount': config.get('sell_amount', 10000),
            'buy_amount_type': config.get('buy_amount_type', 'shares'),
            'sell_amount_type': config.get('sell_amount_type', 'shares'),
        }

        # 报告进度
        call_callback(50, "执行回测策略...")

        # 运行回测
        result = runner.run_single_backtest(full_config)

        # 报告进度
        call_callback(90, "生成分析报告...")

        return result

    @staticmethod
    def _run_all_weather_backtest(
        runner: GridBatchRunner,
        config: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """运行全天候策略回测"""
        # 导入全天候回测引擎
        from backtesting.all_weather_batch_runner import AllWeatherBatchRunner

        # 辅助函数：处理async回调
        def call_callback(progress, message):
            if progress_callback:
                try:
                    progress_callback(progress, message)
                except TypeError:
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(progress_callback(progress, message))
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(progress_callback(progress, message))
                        loop.close()

        # 报告进度
        call_callback(30, "初始化全天候策略回测...")

        # 创建全天候回测运行器
        aw_runner = AllWeatherBatchRunner(initial_cash=runner.initial_cash)

        call_callback(40, "加载ETF数据...")

        # 运行回测
        result = aw_runner.run_backtest(config)

        call_callback(90, "生成分析报告...")

        return result

    @staticmethod
    def validate_grid_config(config: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证网格策略配置

        Args:
            config: 策略配置字典

        Returns:
            (is_valid, error_message)
        """
        required_fields = [
            'etf_code',
            'base_price',
            'grid_spacing_up',
            'grid_spacing_down',
            'buy_amount',
            'sell_amount'
        ]

        # 检查必需字段
        for field in required_fields:
            if field not in config:
                return False, f"缺少必需字段: {field}"

        # 验证数值范围
        if config['base_price'] <= 0:
            return False, "基准价格必须大于0"

        if config['grid_spacing_up'] <= 0 or config['grid_spacing_up'] > 100:
            return False, "上涨网格间距必须在0-100%之间"

        if config['grid_spacing_down'] >= 0 or config['grid_spacing_down'] < -100:
            return False, "下跌网格间距必须在-100%-0%之间"

        if config['buy_amount'] <= 0:
            return False, "买入数量必须大于0"

        if config['sell_amount'] <= 0:
            return False, "卖出数量必须大于0"

        return True, ""

    @staticmethod
    def validate_all_weather_config(config: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证全天候策略配置

        Args:
            config: 策略配置字典

        Returns:
            (is_valid, error_message)
        """
        try:
            # 验证仓位比例
            position_ratio = config.get('position_ratio', 0.5)
            if not isinstance(position_ratio, (int, float)):
                return False, "仓位比例必须是数字"
            if not 0 < position_ratio <= 1:
                return False, "仓位比例必须在0-1之间"

            # 验证再平衡周期
            rebalance_period = config.get('rebalance_period', 60)
            if not isinstance(rebalance_period, int):
                return False, "再平衡周期必须是整数"
            if not 1 <= rebalance_period <= 365:
                return False, "再平衡周期必须在1-365天之间"

            # 验证再平衡阈值
            rebalance_threshold = config.get('rebalance_threshold', 0.05)
            if not isinstance(rebalance_threshold, (int, float)):
                return False, "再平衡阈值必须是数字"
            if not 0 < rebalance_threshold <= 0.5:
                return False, "再平衡阈值必须在0-50%之间"

            # 验证自定义资产配置（如果提供）
            if 'custom_allocation' in config and config['custom_allocation'] is not None:
                custom_alloc = config['custom_allocation']
                if not isinstance(custom_alloc, dict):
                    return False, "自定义资产配置必须是字典类型"

                required_categories = ['commodities', 'stocks', 'long_bonds', 'short_bonds']
                for category in required_categories:
                    if category not in custom_alloc:
                        return False, f"缺少资产类别: {category}"

                    if not isinstance(custom_alloc[category], dict):
                        return False, f"{category} 配置必须是字典"

                    if 'etfs' not in custom_alloc[category]:
                        return False, f"{category} 缺少etfs字段"

                    if not isinstance(custom_alloc[category]['etfs'], list):
                        return False, f"{category}.etfs 必须是列表"

                    if len(custom_alloc[category]['etfs']) == 0:
                        return False, f"{category} 至少需要一个ETF"

            return True, ""

        except Exception as e:
            return False, f"配置验证异常: {str(e)}"



if __name__ == "__main__":
    # 测试回测服务
    import asyncio

    async def test():
        service = BacktestService()

        # 测试配置验证
        config = {
            'etf_code': '560590.SH',
            'base_price': 1.573,
            'grid_spacing_up': 5.0,
            'grid_spacing_down': -5.0,
            'buy_amount': 80000,
            'sell_amount': 80000,
        }

        is_valid, error = service.validate_grid_config(config)
        print(f"配置验证: {is_valid}, 错误: {error}")

    asyncio.run(test())
