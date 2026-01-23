"""诊断513130.SH价格获取问题"""
from data.xtdata_feed import XtDataFeed
import pandas as pd

def main():
    stock_code = '513130.SH'
    xt_feed = XtDataFeed(use_cache=False)

    print(f"诊断 {stock_code} 价格数据问题\n")
    print("=" * 60)

    # 1. 检查上市日期
    try:
        listing_date = xt_feed.get_earliest_date(stock_code)
        print(f"上市日期: {listing_date}")
    except Exception as e:
        print(f"获取上市日期失败: {e}")

    # 2. 测试最近30天数据
    print(f"\n测试最近30天数据:")
    end_date = pd.Timestamp.now().strftime('%Y%m%d')
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime('%Y%m%d')

    recent_data = xt_feed.get_history_data(
        stock_code=stock_code,
        field_list=['open', 'high', 'low', 'close'],
        start_date=start_date,
        end_date=end_date,
        period='1d',
        use_cache=False
    )

    if recent_data is not None and not recent_data.empty:
        print(f"[OK] 最近数据获取成功")
        print(f"  最新收盘价: {recent_data['close'].iloc[-1]:.3f}")
        print(f"  数据行数: {len(recent_data)}")
    else:
        print(f"[FAIL] 最近数据为空")

    # 3. 测试用户回测期间
    print(f"\n测试回测期间 (20240101-20260121):")
    backtest_data = xt_feed.get_history_data(
        stock_code=stock_code,
        field_list=['open', 'high', 'low', 'close'],
        start_date='20240101',
        end_date='20260121',
        period='1d',
        use_cache=False
    )

    if backtest_data is not None and not backtest_data.empty:
        print(f"[OK] 回测数据获取成功")
        print(f"  数据行数: {len(backtest_data)}")
        print(f"  有效价格数: {backtest_data['close'].notna().sum()}")
        print(f"  最新收盘价: {backtest_data['close'].iloc[-1]:.3f}")
    else:
        print(f"[FAIL] 回测数据为空")
        print(f"  建议: 检查回测开始日期是否早于上市日期")

    print("=" * 60)

if __name__ == '__main__':
    main()
