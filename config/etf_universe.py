"""
ETF品种配置
定义所有可交易的ETF品种及其分类
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ETFCategory(Enum):
    """ETF分类枚举"""
    BROAD_INDEX = "broad_index"      # 宽基指数ETF
    SECTOR = "sector"               # 行业ETF
    CROSS_BORDER = "cross_border"   # 跨境ETF
    CUSTOM = "custom"              # 自定义组合

@dataclass
class ETFInfo:
    """ETF信息数据类"""
    code: str                      # ETF代码
    name: str                      # ETF名称
    category: ETFCategory         # ETF分类
    tracking_index: str           # 跟踪指数
    expense_ratio: float          # 管理费率
    min_trade_unit: int = 100     # 最小交易单位
    description: str = ""         # 描述

class ETFUniverse:
    """ETF品种池管理"""

    # 宽基指数ETF
    BROAD_INDEX_ETFS = [
        ETFInfo("510300.SZ", "沪深300ETF", ETFCategory.BROAD_INDEX, "沪深300指数", 0.0020),
        ETFInfo("510500.SZ", "中证500ETF", ETFCategory.BROAD_INDEX, "中证500指数", 0.0020),
        ETFInfo("159919.SZ", "上证50ETF", ETFCategory.BROAD_INDEX, "上证50指数", 0.0030),
        ETFInfo("512880.SZ", "证券ETF", ETFCategory.BROAD_INDEX, "证券公司指数", 0.0080),
        ETFInfo("510810.SZ", "上海国企ETF", ETFCategory.BROAD_INDEX, "上海国企指数", 0.0050),
        ETFInfo("512100.SZ", "中证1000ETF", ETFCategory.BROAD_INDEX, "中证1000指数", 0.0020),
    ]

    # 行业ETF
    SECTOR_ETFS = [
        ETFInfo("512660.SZ", "军工ETF", ETFCategory.SECTOR, "中证军工指数", 0.0080),
        ETFInfo("515880.SZ", "通信ETF", ETFCategory.SECTOR, "通信设备指数", 0.0080),
        ETFInfo("516160.SZ", "新能源ETF", ETFCategory.SECTOR, "中证新能指数", 0.0080),
        ETFInfo("512170.SZ", "医疗ETF", ETFCategory.SECTOR, "中证医疗指数", 0.0080),
        ETFInfo("515050.SZ", "5G ETF", ETFCategory.SECTOR, "中证5G通信主题指数", 0.0080),
        ETFInfo("512800.SZ", "银行ETF", ETFCategory.SECTOR, "中证银行指数", 0.0080),
        ETFInfo("516970.SZ", "基建ETF", ETFCategory.SECTOR, "中证基建指数", 0.0080),
        ETFInfo("512690.SZ", "酒ETF", ETFCategory.SECTOR, "中证酒指数", 0.0080),
        ETFInfo("159928.SZ", "消费ETF", ETFCategory.SECTOR, "消费指数", 0.0080),
        ETFInfo("515700.SZ", "新能源车ETF", ETFCategory.SECTOR, "中证新能源汽车指数", 0.0080),
    ]

    # 跨境ETF
    CROSS_BORDER_ETFS = [
        ETFInfo("513500.SZ", "纳斯达克100ETF", ETFCategory.CROSS_BORDER, "纳斯达克100指数", 0.0080),
        ETFInfo("513100.SZ", "纳指ETF", ETFCategory.CROSS_BORDER, "纳斯达克100指数", 0.0080),
        ETFInfo("159941.SZ", "德国DAX ETF", ETFCategory.CROSS_BORDER, "德国DAX指数", 0.0080),
        ETFInfo("513030.SZ", "德国30 ETF", ETFCategory.CROSS_BORDER, "德国DAX指数", 0.0080),
        ETFInfo("513660.SZ", "恒生科技ETF", ETFCategory.CROSS_BORDER, "恒生科技指数", 0.0080),
        ETFInfo("159920.SZ", "恒生ETF", ETFCategory.CROSS_BORDER, "恒生指数", 0.0080),
    ]

    @classmethod
    def get_all_etfs(cls) -> List[ETFInfo]:
        """获取所有ETF"""
        return cls.BROAD_INDEX_ETFS + cls.SECTOR_ETFS + cls.CROSS_BORDER_ETFS

    @classmethod
    def get_etfs_by_category(cls, category: ETFCategory) -> List[ETFInfo]:
        """根据分类获取ETF"""
        category_map = {
            ETFCategory.BROAD_INDEX: cls.BROAD_INDEX_ETFS,
            ETFCategory.SECTOR: cls.SECTOR_ETFS,
            ETFCategory.CROSS_BORDER: cls.CROSS_BORDER_ETFS,
        }
        return category_map.get(category, [])

    @classmethod
    def get_etf_by_code(cls, code: str) -> ETFInfo:
        """根据代码获取ETF信息"""
        all_etfs = cls.get_all_etfs()
        for etf in all_etfs:
            if etf.code == code:
                return etf
        raise ValueError(f"未找到ETF代码: {code}")

    @classmethod
    def get_etf_codes_by_category(cls, category: ETFCategory) -> List[str]:
        """根据分类获取ETF代码列表"""
        etfs = cls.get_etfs_by_category(category)
        return [etf.code for etf in etfs]

    @classmethod
    def get_default_selection(cls) -> List[str]:
        """获取默认推荐的ETF选择"""
        # 从每个类别选择1-2个代表性ETF
        return [
            "510300.SZ",  # 沪深300ETF - 宽基代表
            "510500.SZ",  # 中证500ETF - 中小盘代表
            "512660.SZ",  # 军工ETF - 行业代表
            "513500.SZ",  # 纳指ETF - 跨境代表
        ]

    @classmethod
    def get_etf_info_dict(cls) -> Dict[str, ETFInfo]:
        """获取ETF信息字典"""
        etf_dict = {}
        for etf in cls.get_all_etfs():
            etf_dict[etf.code] = etf
        return etf_dict

    @classmethod
    def validate_etf_code(cls, code: str) -> bool:
        """验证ETF代码是否有效"""
        try:
            cls.get_etf_by_code(code)
            return True
        except ValueError:
            return False

    @classmethod
    def add_custom_etf(cls, etf_info: ETFInfo) -> None:
        """添加自定义ETF"""
        # 可以扩展为支持用户自定义ETF
        pass

# 默认ETF配置
DEFAULT_ETF_SELECTION = ETFUniverse.get_default_selection()

# ETF权重配置（用于资金分配）
DEFAULT_ETF_WEIGHTS = {
    "510300.SZ": 0.30,  # 沪深300ETF - 30%
    "510500.SZ": 0.25,  # 中证500ETF - 25%
    "512660.SZ": 0.25,  # 军工ETF - 25%
    "513500.SZ": 0.20,  # 纳指ETF - 20%
}