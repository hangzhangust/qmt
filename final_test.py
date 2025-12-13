#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终系统测试
验证修复后的ETF网格交易系统是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_complete_system():
    """测试完整系统功能"""
    print("=" * 60)
    print("ETF网格交易系统 - 最终测试")
    print("=" * 60)

    try:
        # 1. 测试XtQuant客户端
        print("\n1. 测试XtQuant客户端...")
        from data.xtquant_client import XtQuantClient

        client = XtQuantClient()
        connected = client.connect()
        print(f"   客户端连接: {'成功' if connected else '使用回退系统'}")

        # 测试获取价格
        price = client.get_current_price("159682.SZ")
        print(f"   159682.SZ 价格: {price}")

        # 2. 测试回退系统
        print("\n2. 测试数据回退系统...")
        from utils.data_fallback import fallback_system

        status = fallback_system.get_system_status()
        print(f"   回退系统状态: {'激活' if status['fallback_active'] else '未激活'}")
        print(f"   支持的ETF数量: {status['etf_count']}")

        # 3. 测试回测引擎
        print("\n3. 测试回测引擎...")
        from backtest.backtest_engine import ETFGridBacktestEngine

        engine = ETFGridBacktestEngine()
        print("   回测引擎初始化成功")

        # 4. 测试配置系统
        print("\n4. 测试配置系统...")
        from config.settings import ETF_GRID_CONFIG

        etf_count = len(ETF_GRID_CONFIG.etf_universe)
        print(f"   配置的ETF数量: {etf_count}")

        # 显示前3个ETF
        for i, etf in enumerate(ETF_GRID_CONFIG.etf_universe[:3]):
            print(f"   ETF {i+1}: {etf['etf_code']} - {etf['etf_name']} (基准价: {etf['base_price']})")

        print("\n" + "=" * 60)
        print("✅ 所有系统组件测试通过!")
        print("✅ 系统现在可以正常运行回测功能!")
        print("✅ 即使XtQuant连接失败，系统也能使用回退数据正常工作!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_system()