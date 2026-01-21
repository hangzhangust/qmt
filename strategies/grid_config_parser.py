# encoding:utf-8
"""
网格交易策略配置解析器
从 Table.xls 文件解析网格交易策略配置
"""
import pandas as pd
import re
from typing import List, Dict, Any, Tuple
import os


class GridConfigParser:
    """
    网格交易策略配置解析器

    从 Table.xls 文件中提取网格交易策略的配置信息
    """

    @staticmethod
    def parse_table_xls(file_path: str) -> List[Dict[str, Any]]:
        """
        解析 Table.xls 文件并提取所有网格策略配置

        参数:
            file_path: Table.xls 文件路径

        返回:
            List[Dict]: 网格策略配置列表，每个配置包含:
                {
                    'etf_code': str,           # ETF代码
                    'etf_name': str,           # ETF名称
                    'base_price': float,       # 基准价
                    'grid_spacing_up': float,  # 网格上涨间距(%)
                    'grid_spacing_down': float,# 网格下跌间距(%)
                    'buy_amount': float,       # 每格买入金额/数量
                    'sell_amount': float,      # 每格卖出金额/数量
                    'buy_amount_type': str,    # 'shares' 或 'currency'
                    'sell_amount_type': str,   # 'shares' 或 'currency'
                    'created_date': str,       # 创建日期
                    'expiry_date': str,        # 有效期
                }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        # 读取文件，尝试多种编码
        encodings = ['gb18030', 'gbk', 'gb2312', 'utf-8-sig']
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, sep='\t', encoding=encoding)
                print(f"[OK] 使用编码 {encoding} 成功读取配置文件")
                break
            except Exception as e:
                continue

        if df is None:
            raise ValueError("无法读取配置文件，请检查文件格式和编码")

        # 提取配置
        configs = []

        for idx, row in df.iterrows():
            try:
                config = GridConfigParser._parse_row(row)
                if config:
                    configs.append(config)
            except Exception as e:
                print(f"[WARNING] 解析第 {idx+1} 行时出错: {e}")
                continue

        print(f"[OK] 成功解析 {len(configs)} 个网格策略配置")
        return configs

    @staticmethod
    def _parse_row(row: pd.Series) -> Dict[str, Any]:
        """
        解析单行数据

        参数:
            row: DataFrame 的一行

        返回:
            Dict: 网格策略配置字典
        """
        # 使用列索引而不是列名（因为列名有编码问题）
        # 4: 证券代码, 5: 证券名称, 6: 交易模型, 7: 委托方式, 8: 创建时间, 9: 有效日期

        # 提取 ETF 代码（格式：="560590"）
        etf_code_raw = str(row.iloc[4]) if len(row) > 4 else ''
        etf_code_match = re.search(r'"?(\d{6})"?', etf_code_raw)
        if not etf_code_match:
            print(f"[WARNING] 无法解析ETF代码: {etf_code_raw}")
            return None

        etf_code = etf_code_match.group(1)

        # 添加市场后缀（ETF代码通常是6位数字）
        # 需要根据实际情况判断是上海(.SH)还是深圳(.SZ)
        # 这里暂时根据代码首位判断：5=上海，1/3=深圳
        if etf_code.startswith('5'):
            etf_code = f"{etf_code}.SH"
        elif etf_code.startswith('1') or etf_code.startswith('3'):
            etf_code = f"{etf_code}.SZ"
        else:
            # 默认为上海
            etf_code = f"{etf_code}.SH"

        # ETF 名称
        etf_name = str(row.iloc[5]) if len(row) > 5 else ''
        etf_name = etf_name.strip()

        # 提取交易模型描述（索引6）
        model_desc = str(row.iloc[6]) if len(row) > 6 else ''
        model_desc = model_desc.strip()

        if not model_desc or model_desc == 'nan':
            print(f"[WARNING] ETF {etf_code} 缺少交易模型描述")
            return None

        # 解析交易模型参数
        params = GridConfigParser._parse_trigger_condition(model_desc)

        if not params:
            print(f"[WARNING] ETF {etf_code} 无法解析交易模型: {model_desc}")
            return None

        base_price, grid_spacing_up, grid_spacing_down = params[:3]

        # 解析委托金额（索引7）
        commission_method = str(row.iloc[7]) if len(row) > 7 else ''

        # 提取买入金额/数量
        buy_amount, buy_type = GridConfigParser._parse_amount(
            GridConfigParser._extract_buy_amount(commission_method)
        )

        # 提取卖出金额/数量
        sell_amount, sell_type = GridConfigParser._parse_amount(
            GridConfigParser._extract_sell_amount(commission_method)
        )

        # 创建日期和有效期（索引8和9）
        created_date = str(row.iloc[8]) if len(row) > 8 else ''
        created_date = created_date.strip()

        expiry_date = str(row.iloc[9]) if len(row) > 9 else ''
        expiry_date = expiry_date.strip()

        config = {
            'etf_code': etf_code,
            'etf_name': etf_name,
            'base_price': base_price,
            'grid_spacing_up': grid_spacing_up,   # 正数，如 5.0 表示 5%
            'grid_spacing_down': grid_spacing_down, # 负数，如 -5.0 表示 -5%
            'buy_amount': buy_amount,
            'sell_amount': sell_amount,
            'buy_amount_type': buy_type,   # 'shares' 或 'currency'
            'sell_amount_type': sell_type, # 'shares' 或 'currency'
            'created_date': created_date,
            'expiry_date': expiry_date,
        }

        return config

    @staticmethod
    def _parse_trigger_condition(condition_text: str) -> Tuple[float, float, float]:
        """
        解析触发条件文本

        示例: "以1.573元为基准价，每上涨5.00%卖出，每下跌-5.00%买入"

        返回:
            Tuple: (base_price, grid_spacing_up, grid_spacing_down)
        """
        # 提取基准价
        base_price_match = re.search(r'以([\d.]+)元为基准价', condition_text)
        if not base_price_match:
            raise ValueError(f"无法找到基准价: {condition_text}")

        base_price = float(base_price_match.group(1))

        # 提取上涨间距
        up_match = re.search(r'每上涨([\d.]+)%卖出', condition_text)
        if not up_match:
            # 尝试另一种格式
            up_match = re.search(r'上涨([\d.]+)%', condition_text)

        grid_spacing_up = float(up_match.group(1)) if up_match else 5.0

        # 提取下跌间距
        down_match = re.search(r'每下跌-?([\d.]+)%买入', condition_text)
        if not down_match:
            # 尝试另一种格式
            down_match = re.search(r'下跌-?([\d.]+)%', condition_text)

        grid_spacing_down = -float(down_match.group(1)) if down_match else -5.0

        return (base_price, grid_spacing_up, grid_spacing_down)

    @staticmethod
    def _extract_buy_amount(commission_method: str) -> str:
        """
        从委托方式中提取买入金额描述

        示例输入: "限价 买入时 一行 80000份(每份)  卖出时 一行 80000份(每份)"
        返回: "80000份"
        """
        # 查找买入部分
        buy_match = re.search(r'买入时[^\d]+([\d.]+[份元])(?:\([^)]*\))?', commission_method)

        if buy_match:
            return buy_match.group(1)
        else:
            # 尝试另一种格式
            buy_match = re.search(r'买入[^\d]+([\d.]+[份元])', commission_method)
            return buy_match.group(1) if buy_match else "0"

    @staticmethod
    def _extract_sell_amount(commission_method: str) -> str:
        """
        从委托方式中提取卖出金额描述

        示例输入: "限价 买入时 一行 80000份(每份)  卖出时 一行 80000份(每份)"
        返回: "80000份"
        """
        # 查找卖出部分
        sell_match = re.search(r'卖出时[^\d]+([\d.]+[份元])(?:\([^)]*\))?', commission_method)

        if sell_match:
            return sell_match.group(1)
        else:
            # 尝试另一种格式
            sell_match = re.search(r'卖出[^\d]+([\d.]+[份元])', commission_method)
            return sell_match.group(1) if sell_match else "0"

    @staticmethod
    def _parse_amount(amount_str: str) -> Tuple[float, str]:
        """
        解析金额字符串

        参数:
            amount_str: 金额字符串，如 "80000份" 或 "50000.00元"

        返回:
            Tuple: (amount_value, amount_type)
                amount_value: float - 金额数值
                amount_type: str - 'shares' 或 'currency'
        """
        if '份' in amount_str:
            # 提取数字部分
            value_match = re.search(r'([\d.]+)', amount_str)
            value = float(value_match.group(1)) if value_match else 0.0
            return (value, 'shares')
        elif '元' in amount_str:
            # 提取数字部分
            value_match = re.search(r'([\d.]+)', amount_str)
            value = float(value_match.group(1)) if value_match else 0.0
            return (value, 'currency')
        else:
            # 默认为货币
            try:
                value = float(amount_str)
                return (value, 'currency')
            except ValueError:
                return (0.0, 'currency')

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        验证配置的有效性

        参数:
            config: 网格策略配置字典

        返回:
            bool: 配置是否有效
        """
        required_fields = [
            'etf_code', 'etf_name', 'base_price',
            'grid_spacing_up', 'grid_spacing_down',
            'buy_amount', 'sell_amount',
            'buy_amount_type', 'sell_amount_type'
        ]

        for field in required_fields:
            if field not in config:
                print(f"[ERROR] 配置缺少必要字段: {field}")
                return False

        # 验证数值
        if config['base_price'] <= 0:
            print(f"[ERROR] ETF {config['etf_code']} 基准价必须大于0")
            return False

        if config['grid_spacing_up'] <= 0:
            print(f"[ERROR] ETF {config['etf_code']} 网格上涨间距必须大于0")
            return False

        if config['grid_spacing_down'] >= 0:
            print(f"[ERROR] ETF {config['etf_code']} 网格下跌间距必须小于0")
            return False

        if config['buy_amount'] <= 0:
            print(f"[ERROR] ETF {config['etf_code']} 买入金额必须大于0")
            return False

        if config['sell_amount'] <= 0:
            print(f"[ERROR] ETF {config['etf_code']} 卖出金额必须大于0")
            return False

        # 验证金额类型
        if config['buy_amount_type'] not in ['shares', 'currency']:
            print(f"[ERROR] ETF {config['etf_code']} 无效的买入金额类型: {config['buy_amount_type']}")
            return False

        if config['sell_amount_type'] not in ['shares', 'currency']:
            print(f"[ERROR] ETF {config['etf_code']} 无效的卖出金额类型: {config['sell_amount_type']}")
            return False

        return True

    @staticmethod
    def format_config_summary(config: Dict[str, Any]) -> str:
        """
        格式化配置摘要

        参数:
            config: 网格策略配置字典

        返回:
            str: 格式化的配置摘要
        """
        # 使用英文避免Windows控制台编码问题
        amount_type_map = {'shares': 'shares', 'currency': 'CNY'}

        summary = f"""
ETF: {config['etf_code']} ({config['etf_name']})
Base Price: CNY {config['base_price']:.3f}
Grid Spacing: +{config['grid_spacing_up']:.2f}% / {config['grid_spacing_down']:.2f}%
Buy: {config['buy_amount']:.0f} {amount_type_map.get(config['buy_amount_type'], config['buy_amount_type'])}
Sell: {config['sell_amount']:.0f} {amount_type_map.get(config['sell_amount_type'], config['sell_amount_type'])}
Created: {config['created_date']}
Expiry: {config['expiry_date']}
"""
        return summary.strip()


# 测试代码
if __name__ == "__main__":
    # 测试配置解析器
    parser = GridConfigParser()

    # 解析 Table.xls
    configs = parser.parse_table_xls("Table.xls")

    print(f"\n共解析 {len(configs)} 个网格策略配置\n")
    print("=" * 80)

    # 显示所有配置摘要
    for i, config in enumerate(configs, 1):
        print(f"\n【策略 {i}】")
        print(parser.format_config_summary(config))

        # 验证配置
        if parser.validate_config(config):
            print("[OK] Config Valid")
        else:
            print("[ERROR] Config Invalid")

        print("-" * 80)
