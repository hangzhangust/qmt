# encoding:utf-8
"""
状态管理器模块
提供统一的状态持久化接口
"""
import json
import os
from datetime import datetime
from typing import Dict, Any


class StateManager:
    """
    状态管理器
    负责策略状态的保存和恢复
    """

    def __init__(self, state_file: str = None):
        """
        初始化状态管理器

        参数:
            state_file: 状态文件路径
        """
        if state_file is None:
            home_dir = os.path.expanduser("~")
            state_dir = os.path.join(home_dir, "QMT_Strategy_Data")
            if not os.path.exists(state_dir):
                os.makedirs(state_dir)
            state_file = os.path.join(state_dir, "strategy_state.json")

        self.state_file = state_file

    def save_state(self, strategy_name: str, state_dict: Dict[str, Any]) -> None:
        """
        保存策略状态

        参数:
            strategy_name: 策略名称
            state_dict: 状态字典
        """
        try:
            # 加载现有状态
            full_state = self.load_full_state()

            # 更新策略状态
            full_state[strategy_name] = state_dict
            full_state['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 保存到文件
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(full_state, f, ensure_ascii=False, indent=2)

            print(f"策略状态已保存: {strategy_name}")

        except Exception as e:
            print(f"保存状态失败: {e}")

    def load_state(self, strategy_name: str) -> Dict[str, Any]:
        """
        加载策略状态

        参数:
            strategy_name: 策略名称

        返回:
            dict: 策略状态，如果不存在返回空字典
        """
        try:
            full_state = self.load_full_state()
            return full_state.get(strategy_name, {})

        except Exception as e:
            print(f"加载状态失败: {e}")
            return {}

    def load_full_state(self) -> Dict[str, Any]:
        """
        加载完整的状态文件

        返回:
            dict: 完整状态字典
        """
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}

        except Exception as e:
            print(f"加载状态文件失败: {e}")
            return {}

    def delete_state(self, strategy_name: str) -> None:
        """
        删除策略状态

        参数:
            strategy_name: 策略名称
        """
        try:
            full_state = self.load_full_state()

            if strategy_name in full_state:
                del full_state[strategy_name]
                full_state['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 保存更新后的状态
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(full_state, f, ensure_ascii=False, indent=2)

                print(f"策略状态已删除: {strategy_name}")

        except Exception as e:
            print(f"删除状态失败: {e}")

    def get_all_strategies(self) -> list:
        """
        获取所有有状态记录的策略

        返回:
            list: 策略名称列表
        """
        full_state = self.load_full_state()
        strategies = [key for key in full_state.keys() if key != 'last_updated']
        return strategies

    def clear_all_states(self) -> None:
        """
        清除所有策略状态
        """
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            print("所有策略状态已清除")

        except Exception as e:
            print(f"清除状态失败: {e}")
