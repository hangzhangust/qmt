#coding:gbk
"""
ETF网格交易策略主程序
基于XtQuant实现自动化ETF网格交易
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import CONFIG, ETF_GRID_CONFIG, RISK_CONFIG, BACKTEST_CONFIG
from strategy.grid_engine import ETFGridStrategy
from data.xtquant_client import XtQuantClient
from execution.order_executor import ETFOrderExecutor
from risk.risk_manager import ETFGridRiskManager
from backtest.backtest_engine import ETFGridBacktestEngine
from utils.logger import get_logger

class ETFGridTradingSystem:
    """ETF网格交易系统主类"""

    def __init__(self):
        """初始化交易系统"""
        self.logger = get_logger("ETFGridTradingSystem")

        # 系统配置
        self.total_capital = CONFIG.TOTAL_CAPITAL
        self.etf_codes = [config['etf_code'] for config in ETF_GRID_CONFIG.etf_universe]

        # 核心组件
        self.data_client = None
        self.order_executor = None
        self.risk_manager = None
        self.strategies = {}  # ETF策略实例

        # 运行状态
        self.is_running = False
        self.main_thread = None

        # 统计信息
        self.system_stats = {
            'start_time': None,
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_pnl': 0.0,
            'risk_alerts': 0,
            'last_update': None
        }

        self.logger.info("ETF网格交易系统初始化完成")

    def initialize(self) -> bool:
        """初始化系统组件"""
        try:
            self.logger.info("正在初始化ETF网格交易系统...")

            # 1. 初始化数据客户端
            self.data_client = XtQuantClient(
                data_dir=ETF_GRID_CONFIG.qmt_data_dir,
                session_id=ETF_GRID_CONFIG.session_id
            )

            if not self.data_client.connect():
                self.logger.error("数据客户端连接失败")
                return False

            # 2. 初始化订单执行器
            self.order_executor = ETFOrderExecutor(
                session_id=ETF_GRID_CONFIG.session_id
            )

            # 3. 初始化风险管理器
            self.risk_manager = ETFGridRiskManager(self.total_capital)

            # 4. 初始化ETF策略
            capital_per_etf = self.total_capital / len(self.etf_codes)
            for etf_code in self.etf_codes:
                try:
                    strategy = ETFGridStrategy(etf_code, capital_per_etf)
                    self.strategies[etf_code] = strategy
                    self.logger.info(f"ETF策略初始化: {etf_code}")
                except Exception as e:
                    self.logger.error(f"ETF策略初始化失败 {etf_code}: {str(e)}")

            self.logger.info("系统初始化完成")
            return True

        except Exception as e:
            self.logger.error(f"系统初始化失败: {str(e)}")
            return False

    def start(self, mode: str = "live") -> bool:
        """
        启动交易系统

        Args:
            mode: 运行模式 - "live"(实盘) 或 "paper"(模拟)
        """
        try:
            if self.is_running:
                self.logger.warning("系统已在运行中")
                return True

            if mode == "paper":
                self.order_executor.enable_simulation = True
                self.logger.info("启动模拟交易模式")
            else:
                self.logger.info("启动实盘交易模式")

            # 初始化系统
            if not self.initialize():
                return False

            # 初始化策略
            if not self._initialize_strategies():
                return False

            # 启动策略
            for etf_code, strategy in self.strategies.items():
                if strategy.start():
                    self.logger.info(f"策略已启动: {etf_code}")

            # 启动主循环
            self.is_running = True
            self.system_stats['start_time'] = datetime.now()
            self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
            self.main_thread.start()

            self.logger.info("ETF网格交易系统已启动")
            return True

        except Exception as e:
            self.logger.error(f"系统启动失败: {str(e)}")
            return False

    def stop(self):
        """停止交易系统"""
        if not self.is_running:
            return

        self.logger.info("正在停止ETF网格交易系统...")

        # 停止主循环
        self.is_running = False

        # 等待主线程结束
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=5)

        # 停止所有策略
        for etf_code, strategy in self.strategies.items():
            try:
                strategy.stop()
                self.logger.info(f"策略已停止: {etf_code}")
            except Exception as e:
                self.logger.error(f"停止策略失败 {etf_code}: {str(e)}")

        # 清理待处理订单
        if self.order_executor:
            pending_orders = self.order_executor.get_pending_orders()
            for order in pending_orders:
                self.order_executor.cancel_order(order.order_id)

        # 断开连接
        if self.data_client:
            self.data_client.disconnect()

        self.logger.info("ETF网格交易系统已停止")

    def _initialize_strategies(self) -> bool:
        """初始化所有策略"""
        try:
            for etf_code, strategy in self.strategies.items():
                # 获取当前价格
                current_price = self._get_current_price(etf_code)
                if current_price <= 0:
                    self.logger.warning(f"无法获取 {etf_code} 的当前价格，使用配置中的基准价格")
                    current_price = None

                # 初始化策略
                if not strategy.initialize(current_price):
                    self.logger.error(f"策略初始化失败: {etf_code}")
                    return False

                # 订阅实时行情
                if self.data_client:
                    self.data_client.subscribe_quote(
                        etf_code,
                        callback=lambda data, code=etf_code: self._on_market_data(code, data),
                        period='1m'
                    )

            return True

        except Exception as e:
            self.logger.error(f"策略初始化失败: {str(e)}")
            return False

    def _get_current_price(self, etf_code: str) -> float:
        """获取ETF当前价格"""
        try:
            if self.data_client and self.data_client.is_connected:
                data = self.data_client.get_market_data([etf_code], count=1)
                if data and etf_code in data:
                    return float(data[etf_code].get('close', 0))

            # 从配置中获取基准价格作为后备
            etf_config = ETF_GRID_CONFIG.get_etf_config(etf_code)
            if etf_config:
                return etf_config['base_price']

            return 0.0

        except Exception as e:
            self.logger.error(f"获取价格失败 {etf_code}: {str(e)}")
            return 0.0

    def _main_loop(self):
        """主循环"""
        self.logger.info("主循环已启动")

        while self.is_running:
            try:
                # 1. 更新市场数据
                self._update_market_data()

                # 2. 检查风险控制
                self._check_risk_control()

                # 3. 清理过期订单
                self._cleanup_expired_data()

                # 4. 更新统计信息
                self._update_statistics()

                # 5. 等待下次循环
                time.sleep(CONFIG.REALTIME_UPDATE_INTERVAL)

            except Exception as e:
                self.logger.error(f"主循环异常: {str(e)}")
                time.sleep(5)

        self.logger.info("主循环已退出")

    def _update_market_data(self):
        """更新市场数据"""
        try:
            for etf_code, strategy in self.strategies.items():
                if not strategy.is_running:
                    continue

                # 获取当前价格
                current_price = self._get_current_price(etf_code)
                if current_price > 0:
                    # 更新策略价格
                    signals = strategy.update_price(current_price)

                    # 执行交易信号
                    if signals:
                        self._execute_signals(signals)

                    # 更新风险管理器
                    self.risk_manager.update_market_data(etf_code, current_price)

        except Exception as e:
            self.logger.error(f"更新市场数据异常: {str(e)}")

    def _on_market_data(self, etf_code: str, data: Dict[str, Any]):
        """市场数据回调"""
        try:
            if not self.is_running or etf_code not in self.strategies:
                return

            strategy = self.strategies[etf_code]
            if not strategy.is_running:
                return

            # 提取价格信息
            if 'close' in data:
                current_price = float(data['close'])
                if current_price > 0:
                    # 更新策略价格
                    signals = strategy.update_price(current_price)

                    # 执行交易信号
                    if signals:
                        self._execute_signals(signals)

                    # 更新风险管理器
                    self.risk_manager.update_market_data(etf_code, current_price)

        except Exception as e:
            self.logger.error(f"市场数据回调异常 {etf_code}: {str(e)}")

    def _execute_signals(self, signals: List[Dict[str, Any]]):
        """执行交易信号"""
        try:
            for signal in signals:
                # 风险检查
                passed, risk_messages = self.risk_manager.check_pre_trade_risk(
                    symbol=signal['symbol'],
                    action=signal['action'],
                    quantity=signal['quantity'],
                    price=signal['price']
                )

                if not passed:
                    self.logger.warning(f"交易信号被风险控制拦截: {signal['symbol']} {signal['action']}, "
                                     f"风险: {risk_messages}")
                    continue

                # 执行订单
                result = self.order_executor.place_order(
                    symbol=signal['symbol'],
                    direction=signal['action'],
                    quantity=signal['quantity'],
                    price=signal['price']
                )

                if result.success:
                    # 更新风险管理器持仓
                    self.risk_manager.update_position(
                        symbol=signal['symbol'],
                        quantity=signal['quantity'],
                        price=signal['price'],
                        action=signal['action'],
                        commission=self.order_executor.execution_stats.get('total_commission', 0) / max(1, self.order_executor.execution_stats.get('total_orders', 1))
                    )

                    # 更新策略
                    strategy = self.strategies.get(signal['symbol'])
                    if strategy:
                        strategy.execute_trade(signal, result.order_id)

                    self.system_stats['total_trades'] += 1
                    self.system_stats['successful_trades'] += 1

                    self.logger.info(f"订单执行成功: {signal['action']} {signal['quantity']}股 {signal['symbol']} @?{signal['price']:.3f}")
                else:
                    self.system_stats['total_trades'] += 1
                    self.system_stats['failed_trades'] += 1

                    self.logger.error(f"订单执行失败: {result.message}")

        except Exception as e:
            self.logger.error(f"执行交易信号异常: {str(e)}")

    def _check_risk_control(self):
        """检查风险控制"""
        try:
            # 检查是否需要停止交易
            if self.risk_manager.should_stop_trading():
                self.logger.critical("触发风险控制，停止所有交易")
                self.stop()

        except Exception as e:
            self.logger.error(f"风险控制检查异常: {str(e)}")

    def _cleanup_expired_data(self):
        """清理过期数据"""
        try:
            # 清理过期订单
            if self.order_executor:
                self.order_executor.cleanup_expired_orders()

            # 清理旧的告警
            if self.risk_manager:
                self.risk_manager.clear_old_alerts()

        except Exception as e:
            self.logger.error(f"清理过期数据异常: {str(e)}")

    def _update_statistics(self):
        """更新统计信息"""
        try:
            self.system_stats['last_update'] = datetime.now()

            # 更新总盈亏
            total_pnl = 0.0
            for strategy in self.strategies.values():
                total_pnl += strategy.calculate_daily_pnl()
            self.system_stats['total_pnl'] = total_pnl

            # 更新风险告警数
            if self.risk_manager:
                self.system_stats['risk_alerts'] = len(self.risk_manager.risk_alerts)

        except Exception as e:
            self.logger.error(f"更新统计信息异常: {str(e)}")

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                'is_running': self.is_running,
                'system_stats': self.system_stats.copy(),
                'strategies': {},
                'risk_status': None,
                'execution_stats': None
            }

            # 策略状态
            for etf_code, strategy in self.strategies.items():
                status['strategies'][etf_code] = strategy.get_status()

            # 风险状态
            if self.risk_manager:
                status['risk_status'] = self.risk_manager.get_risk_status()

            # 执行统计
            if self.order_executor:
                status['execution_stats'] = self.order_executor.get_execution_stats()

            return status

        except Exception as e:
            self.logger.error(f"获取系统状态异常: {str(e)}")
            return {'error': str(e)}

def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("ETF网格交易策略回测")
    print("=" * 60)

    try:
        # 创建回测引擎
        backtest_engine = ETFGridBacktestEngine()

        # 选择要回测的ETF
        etf_codes = ["159682", "159380", "159985"]  # 可以修改为需要的ETF代码

        # 运行回测
        results = backtest_engine.run_portfolio_backtest(etf_codes)

        # 生成报告
        report_content = backtest_engine.generate_report(results)

        # 保存报告
        report_path = f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"\n回测完成！报告已保存至: {report_path}")
        print("\n" + report_content)

    except Exception as e:
        print(f"回测失败: {str(e)}")

def main():
    """主函数"""
    print("ETF网格交易策略系统")
    print("=" * 40)
    print("1. 实盘交易")
    print("2. 模拟交易")
    print("3. 运行回测")
    print("4. 退出")
    print("=" * 40)

    while True:
        try:
            choice = input("\n请选择功能 (1-4): ").strip()

            if choice == "1":
                print("启动实盘交易...")
                system = ETFGridTradingSystem()
                if system.start("live"):
                    print("实盘交易系统已启动，按 Ctrl+C 停止")
                    try:
                        while True:
                            time.sleep(10)
                            # 显示系统状态
                            status = system.get_system_status()
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                                  f"运行中 | 总交易: {status['system_stats']['total_trades']} | "
                                  f"总盈亏: {status['system_stats']['total_pnl']:+.2f}")
                    except KeyboardInterrupt:
                        print("\n正在停止系统...")
                        system.stop()
                        print("系统已停止")
                break

            elif choice == "2":
                print("启动模拟交易...")
                system = ETFGridTradingSystem()
                if system.start("paper"):
                    print("模拟交易系统已启动，按 Ctrl+C 停止")
                    try:
                        while True:
                            time.sleep(10)
                            # 显示系统状态
                            status = system.get_system_status()
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                                  f"模拟运行 | 总交易: {status['system_stats']['total_trades']} | "
                                  f"总盈亏: {status['system_stats']['total_pnl']:+.2f}")
                    except KeyboardInterrupt:
                        print("\n正在停止系统...")
                        system.stop()
                        print("系统已停止")
                break

            elif choice == "3":
                run_backtest()
                break

            elif choice == "4":
                print("退出系统")
                break

            else:
                print("无效选择，请输入 1-4")

        except KeyboardInterrupt:
            print("\n\n用户中断，退出系统")
            break
        except Exception as e:
            print(f"操作异常: {str(e)}")

if __name__ == "__main__":
    main()