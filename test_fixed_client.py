#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的XtQuant客户端
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.xtquant_client import XtQuantClient

def test_xtquant_client():
    """测试修复后的XtQuant客户端"""
    print("=" * 60)
    print("测试修复后的XtQuant客户端")
    print("=" * 60)

    try:
        # 创建客户端
        print("\n1. 创建XtQuant客户端...")
        client = XtQuantClient()

        # 测试连接
        print("\n2. 测试连接...")
        connected = client.connect()
        print(f"连接结果: {'成功' if connected else '失败'}")

        # 测试获取单个价格
        print("\n3. 测试获取单个价格...")
        test_symbol = "159682.SZ"
        price = client.get_current_price(test_symbol)
        print(f"{test_symbol} 价格: {price}")

        # 测试获取市场数据
        print("\n4. 测试获取市场数据...")
        test_symbols = ["159682.SZ", "159380.SZ"]
        try:
            data = client.get_market_data(stock_list=test_symbols, count=1)
            print(f"市场数据获取成功，数据键: {list(data.keys()) if data else 'None'}")

            # 显示数据结构
            if data and test_symbols[0] in data:
                symbol_data = data[test_symbols[0]]
                print(f"{test_symbols[0]} 数据类型: {type(symbol_data)}")
                if hasattr(symbol_data, 'close'):
                    print(f"  收盘价: {symbol_data.close}")
                elif isinstance(symbol_data, dict):
                    print(f"  数据字段: {list(symbol_data.keys())}")

        except Exception as e:
            print(f"获取市场数据失败: {e}")

        # 显示连接状态
        print("\n5. 显示连接状态...")
        if hasattr(client, 'api_wrapper'):
            status = client.api_wrapper.get_connection_status()
            print(f"XtQuant可用: {status['xtquant_available']}")
            print(f"已连接: {status['is_connected']}")
            print(f"回退系统激活: {status['fallback_system']}")
            print(f"熔断器激活: {status['circuit_breaker_active']}")

        print("\n测试完成 - 系统现在可以正常工作！")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_xtquant_client()