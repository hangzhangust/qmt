# encoding:utf-8
"""
配置加载器模块
提供统一的配置加载和验证功能
"""
import json
import os
from typing import Dict, Any


class ConfigLoader:
    """
    配置加载器
    加载并验证策略配置
    """

    @staticmethod
    def load_strategy_config(config_file: str = None) -> Dict[str, Any]:
        """
        加载策略配置

        参数:
            config_file: 配置文件路径，默认为~/QMT_Strategy_Data/strategy_config.json

        返回:
            dict: 配置字典
        """
        if config_file is None:
            home_dir = os.path.expanduser("~")
            config_file = os.path.join(home_dir, "QMT_Strategy_Data", "strategy_config.json")

        # 默认配置
        default_config = {
            # 全天候策略配置
            "all_weather_position_ratio": 0.5,
            "rebalance_threshold": 0.05,
            "rebalance_period": 60,

            # 动量策略配置
            "momentum_position_ratio": 0.5,
            "lookback_period": 20,
            "hold_period": 20,

            # 风控参数
            "max_drawdown_threshold": 10,

            # XtQuant配置（新增）
            "xtquant_path": "",
            "xtquant_session_id": 123456,
            "xtquant_account_id": "",

            # 数据缓存配置
            "cache_enabled": True,
            "cache_expire_days": 7,

            # 重连延迟配置（避免session冲突）
            "reconnect_delay": 3.0,  # 断开后重连前的等待时间（秒）
        }

        # 尝试加载配置文件
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                print(f"加载配置文件: {config_file}")

                # 合并配置（用户配置覆盖默认配置）
                config = {**default_config, **user_config}

                # 验证配置
                ConfigLoader._validate_config(config)

                return config
            else:
                print(f"配置文件不存在，使用默认配置: {config_file}")
                # 创建默认配置文件
                ConfigLoader._save_default_config(config_file, default_config)
                return default_config

        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return default_config

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """
        验证配置参数

        参数:
            config: 配置字典

        异常:
            ValueError: 配置参数不合法
        """
        # 验证仓位比例
        if 'all_weather_position_ratio' in config:
            pr = config['all_weather_position_ratio']
            if not 0 < pr <= 1:
                raise ValueError(f"all_weather_position_ratio必须在(0,1]范围内，当前值: {pr}")

        if 'momentum_position_ratio' in config:
            pr = config['momentum_position_ratio']
            if not 0 < pr <= 1:
                raise ValueError(f"momentum_position_ratio必须在(0,1]范围内，当前值: {pr}")

        # 验证再平衡周期
        if 'rebalance_period' in config:
            rp = config['rebalance_period']
            if not isinstance(rp, int) or rp < 1:
                raise ValueError(f"rebalance_period必须是正整数，当前值: {rp}")

        # 验证阈值
        if 'rebalance_threshold' in config:
            rt = config['rebalance_threshold']
            if not 0 < rt <= 1:
                raise ValueError(f"rebalance_threshold必须在(0,1]范围内，当前值: {rt}")

        # Validate xtquant_path if provided
        if 'xtquant_path' in config and config['xtquant_path']:
            path = config['xtquant_path']
            if not os.path.exists(path):
                print(f"Warning: xtquant_path does not exist: {path}")
                print(f"Please verify the QMT installation path")

        # Validate timeout settings
        if 'api_timeout' in config:
            timeout = config['api_timeout']
            if not isinstance(timeout, (int, float)) or timeout < 0.1 or timeout > 60:
                raise ValueError(f"api_timeout must be between 0.1 and 60 seconds, current: {timeout}")

        if 'max_retries' in config:
            retries = config['max_retries']
            if not isinstance(retries, int) or retries < 0 or retries > 10:
                raise ValueError(f"max_retries must be between 0 and 10, current: {retries}")

        if 'callback_timeout' in config:
            cb_timeout = config['callback_timeout']
            if not isinstance(cb_timeout, (int, float)) or cb_timeout < 0.1 or cb_timeout > 10:
                raise ValueError(f"callback_timeout must be between 0.1 and 10 seconds, current: {cb_timeout}")

        print("配置验证通过")

    @staticmethod
    def _save_default_config(config_file: str, config: Dict[str, Any]) -> None:
        """
        保存默认配置到文件

        参数:
            config_file: 配置文件路径
            config: 配置字典
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            print(f"创建默认配置文件: {config_file}")

        except Exception as e:
            print(f"保存配置文件失败: {e}")

    @staticmethod
    def save_config(config: Dict[str, Any], config_file: str = None) -> bool:
        """
        保存配置到文件

        参数:
            config: 配置字典
            config_file: 配置文件路径

        返回:
            bool: 是否成功
        """
        if config_file is None:
            home_dir = os.path.expanduser("~")
            config_file = os.path.join(home_dir, "QMT_Strategy_Data", "strategy_config.json")

        try:
            # 验证配置
            ConfigLoader._validate_config(config)

            # 确保目录存在
            config_dir = os.path.dirname(config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            print(f"配置已保存: {config_file}")
            return True

        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
