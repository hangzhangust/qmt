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
        # 报告进度
        if progress_callback:
            asyncio.create_task(progress_callback(30, "加载市场数据..."))

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
        if progress_callback:
            asyncio.create_task(progress_callback(50, "执行回测策略..."))

        # 运行回测
        result = runner.run_single_backtest(full_config)

        # 报告进度
        if progress_callback:
            asyncio.create_task(progress_callback(90, "生成分析报告..."))

        return result

    @staticmethod
    def _run_all_weather_backtest(
        runner: GridBatchRunner,
        config: Dict[str, Any],
        progress_callback=None
    ) -> Dict[str, Any]:
        """运行全天候策略回测（待实现）"""
        # TODO: 实现全天候策略回测
        raise NotImplementedError("全天候策略回测功能待实现")

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
