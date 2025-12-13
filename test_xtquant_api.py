#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XtQuant API Test Script
用于测试和验证XtQuant API的正确用法
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import xtquant.xtdata as xtdata
    print("XtQuant库导入成功")
except ImportError as e:
    print(f"XtQuant库导入失败: {e}")
    print("请确保已安装XtQuant库并且QMT终端正在运行")
    sys.exit(1)

def test_api_signature():
    """测试XtQuant API的参数签名"""
    print("\n" + "="*60)
    print("XtQuant API 签名测试")
    print("="*60)

    # 测试get_market_data的不同参数组合
    test_cases = [
        {
            "name": "测试1: symbols参数",
            "params": {
                "symbols": ["000001.SZ"],
                "fields": ["open", "high", "low", "close", "volume"],
                "period": "1d",
                "count": 1
            }
        },
        {
            "name": "测试2: stock_list参数",
            "params": {
                "stock_list": ["000001.SZ"],
                "period": "1d",
                "count": 1,
                "dividend_type": "none",
                "fill_data": True
            }
        },
        {
            "name": "测试3: 带data_dir参数",
            "params": {
                "symbols": ["000001.SZ"],
                "period": "1d",
                "count": 1,
                "data_dir": r"C:\Users\zhanghang\国金证券QMT交易端\datadir"
            }
        },
        {
            "name": "测试4: 完整参数",
            "params": {
                "symbols": ["000001.SZ", "159682.SZ"],
                "fields": ["open", "high", "low", "close", "volume", "amount"],
                "period": "1d",
                "count": 5,
                "dividend_type": "none",
                "fill_data": True
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            result = xtdata.get_market_data(**test_case['params'])
            print(f"成功: 返回数据类型 {type(result)}")
            if result is not None:
                if hasattr(result, 'keys'):
                    print(f"   数据键: {list(result.keys())}")
                else:
                    print(f"   数据内容: {result}")
            else:
                print("   返回: None")

        except Exception as e:
            print(f"失败: {type(e).__name__}: {str(e)}")

def test_connection_status():
    """测试连接状态"""
    print("\n" + "="*60)
    print("XtQuant 连接状态测试")
    print("="*60)

    try:
        # 测试连接状态
        print("测试基本连接...")
        status = xtdata.get_client_logined_status()
        print(f"连接状态: {status}")

        # 测试获取基本信息
        print("\n测试获取交易时间...")
        trading_days = xtdata.get_trading_dates("SZ", "20240101", "20241231")
        if trading_days is not None and len(trading_days) > 0:
            print(f"交易日期获取成功，最近交易日: {trading_days[-1]}")
        else:
            print("交易日期获取失败或为空")

    except Exception as e:
        print(f"连接测试失败: {type(e).__name__}: {str(e)}")

def test_etf_data():
    """测试ETF数据获取"""
    print("\n" + "="*60)
    print("ETF数据获取测试")
    print("="*60)

    etf_codes = ["159682.SZ", "159380.SZ", "159985.SZ"]  # 配置文件中的ETF代码

    for etf_code in etf_codes:
        print(f"\n测试ETF: {etf_code}")

        # 尝试不同的参数组合
        attempts = [
            {"symbols": [etf_code], "period": "1d", "count": 1},
            {"stock_list": [etf_code], "period": "1d", "count": 1},
            {"symbols": [etf_code], "fields": ["close"], "period": "1d", "count": 1}
        ]

        for i, params in enumerate(attempts, 1):
            try:
                result = xtdata.get_market_data(**params)
                print(f"   尝试{i}: 成功获取数据")
                if result and etf_code in result:
                    data = result[etf_code]
                    if hasattr(data, 'close'):
                        print(f"      最新收盘价: {data.close}")
                    break
            except Exception as e:
                print(f"   尝试{i}: {str(e)}")

def main():
    """主函数"""
    print("XtQuant API 测试脚本")
    print("测试目标: 确定正确的get_market_data参数签名")

    # 基本API签名测试
    test_api_signature()

    # 连接状态测试
    test_connection_status()

    # ETF数据测试
    test_etf_data()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print("\n请将上述结果提供给开发者，以确定正确的API用法")

if __name__ == "__main__":
    main()