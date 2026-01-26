"""
市场数据API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建路由器
router = APIRouter()

# 尝试导入数据接口
try:
    from xtdata import xtdata
    HAS_XTDATA = True
except ImportError:
    HAS_XTDATA = False
    print("[MarketData API] 警告: 未找到xtdata模块，将使用模拟数据")


# ==================== 请求/响应模型 ====================

class CurrentPriceResponse(BaseModel):
    """当前价格响应"""
    etf_code: str
    price: float
    timestamp: str


class BatchPriceResponse(BaseModel):
    """批量价格响应"""
    prices: Dict[str, float]


# ==================== API接口 ====================

@router.get("/current-price/{etf_code}", response_model=CurrentPriceResponse)
async def get_current_price(etf_code: str):
    """
    获取ETF当前价格

    Args:
        etf_code: ETF代码，如 513130.SH

    Returns:
        当前价格信息
    """
    try:
        price = None

        if HAS_XTDATA:
            # 使用miniQMT数据接口获取最新价格
            try:
                tick_data = xtdata.get_market_data(
                    field_list=['close'],
                    stock_list=[etf_code],
                    period='1d',
                    count=1,
                    dividend_type='none'  # ETFs don't support dividend adjustment
                )

                if tick_data and etf_code in tick_data:
                    df = tick_data[etf_code]
                    if df is not None and not df.empty:
                        price = float(df['close'].iloc[-1])
            except Exception as e:
                print(f"[MarketData API] 获取实时数据失败: {e}")
                # 继续尝试其他方法

        # 如果无法获取实时数据，尝试从数据库或历史数据中获取
        if price is None or price == 0:
            # TODO: 可以从数据库或历史数据文件中获取最新价格
            # 暂时返回错误
            raise HTTPException(
                status_code=404,
                detail=f"无法获取 {etf_code} 的价格数据，请确保数据接口正常工作"
            )

        from datetime import datetime
        return CurrentPriceResponse(
            etf_code=etf_code,
            price=price,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"获取价格失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/batch-prices", response_model=BatchPriceResponse)
async def get_batch_prices(etf_codes: List[str]):
    """
    批量获取ETF当前价格

    Args:
        etf_codes: ETF代码列表

    Returns:
        价格字典 {etf_code: price}
    """
    try:
        prices = {}

        if HAS_XTDATA:
            # 使用miniQMT数据接口批量获取最新价格
            try:
                tick_data = xtdata.get_market_data(
                    field_list=['close'],
                    stock_list=etf_codes,
                    period='1d',
                    count=1,
                    dividend_type='none'
                )

                for etf_code in etf_codes:
                    if tick_data and etf_code in tick_data:
                        df = tick_data[etf_code]
                        if df is not None and not df.empty:
                            prices[etf_code] = float(df['close'].iloc[-1])
                        else:
                            prices[etf_code] = 0.0
                    else:
                        prices[etf_code] = 0.0
            except Exception as e:
                print(f"[MarketData API] 批量获取数据失败: {e}")
                # 返回所有0
                for etf_code in etf_codes:
                    prices[etf_code] = 0.0
        else:
            # 如果没有xtdata，返回所有0
            for etf_code in etf_codes:
                prices[etf_code] = 0.0

        return BatchPriceResponse(prices=prices)

    except Exception as e:
        import traceback
        error_msg = f"批量获取价格失败: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    print("市场数据API路由模块")
    print("使用 uvicorn main:app 启动服务器")
