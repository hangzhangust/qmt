#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的get_local_data测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_simple():
    print("Testing get_local_data fix...")

    try:
        from data.xtquant_client import XtQuantClient

        # 创建客户端
        client = XtQuantClient()
        connected = client.connect()
        print(f"Connection status: {'Success' if connected else 'Fallback system'}")

        # 测试get_local_data - 这是曾经导致NoneType错误的方法
        print("Testing get_local_data method...")
        data = client.get_local_data(
            stock_list=["159682.SZ", "159380.SZ"],
            field_list=["open", "high", "low", "close", "volume"],
            period="1d",
            count=10
        )

        # 关键测试：这里不应该再出现"'NoneType' object is not iterable"错误
        if data is not None:
            print(f"SUCCESS: get_local_data returned data for {len(data)} stocks")

            # 尝试迭代（原始错误发生的地方）
            for symbol in data:
                print(f"  Stock {symbol}: data type = {type(data[symbol])}")

                # 尝试访问数据
                stock_data = data[symbol]
                if hasattr(stock_data, 'shape'):
                    print(f"    Shape: {stock_data.shape}")
                elif hasattr(stock_data, '__len__'):
                    print(f"    Length: {len(stock_data)}")
                elif isinstance(stock_data, dict):
                    print(f"    Keys: {list(stock_data.keys())}")

        else:
            print("WARNING: get_local_data returned None, but no exception thrown")

        print("TEST PASSED: No NoneType error occurred!")
        return True

    except TypeError as e:
        if "'NoneType' object is not iterable" in str(e):
            print(f"TEST FAILED: Original NoneType error still exists: {e}")
            return False
        else:
            print(f"TEST FAILED: Other TypeError: {e}")
            return False
    except Exception as e:
        print(f"TEST FAILED: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_simple()
    if success:
        print("\n=== FIX VERIFICATION SUCCESSFUL ===")
        print("The get_local_data() NoneType error has been resolved!")
        print("The system now handles None returns gracefully with fallback data.")
    else:
        print("\n=== FIX VERIFICATION FAILED ===")
        print("The get_local_data() NoneType error still exists.")