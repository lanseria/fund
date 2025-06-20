# src/python_cli_starter/strategies/moving_average_cross_strategy.py

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# --- 策略常量 ---
FAST_MA_PERIOD = 20
SLOW_MA_PERIOD = 60

def get_latest_fund_data(fund_symbol: str) -> pd.DataFrame:
    """获取基金最近150天的净值数据"""
    logger.info(f"[MA Cross Strategy] 正在为基金 {fund_symbol} 获取最新净值数据...")
    start_date = (datetime.today() - timedelta(days=150)).strftime('%Y%m%d')
    
    try:
        fund_nav_df = ak.fund_open_fund_info_em(symbol=fund_symbol, indicator="单位净值走势")
        fund_nav_df['净值日期'] = pd.to_datetime(fund_nav_df['净值日期'])
        fund_nav_df = fund_nav_df.set_index('净值日期')
        fund_nav_df = fund_nav_df[['单位净值']]
        fund_nav_df.columns = ['close']
        fund_nav_df['close'] = pd.to_numeric(fund_nav_df['close'])
        
        fund_nav_df = fund_nav_df[fund_nav_df.index >= start_date].sort_index(ascending=True)
        
        if fund_nav_df.empty or len(fund_nav_df) < SLOW_MA_PERIOD + 2:
            logger.warning(f"[MA Cross Strategy] 获取到的数据为空或数据量不足以判断交叉。")
            return None
            
        logger.info(f"[MA Cross Strategy] 数据获取成功，共 {len(fund_nav_df)} 条记录。")
        return fund_nav_df
        
    except Exception as e:
        logger.error(f"[MA Cross Strategy] 获取基金 {fund_symbol} 数据时发生错误: {e}")
        return None

def calculate_moving_averages(data: pd.DataFrame, fast_period: int, slow_period: int) -> pd.DataFrame:
    """计算快线和慢线。"""
    data['fast_ma'] = data['close'].rolling(window=fast_period).mean()
    data['slow_ma'] = data['close'].rolling(window=slow_period).mean()
    return data

def run_strategy(fund_code: str, is_holding: bool) -> Dict[str, Any]:
    """执行双均线交叉策略并返回决策结果。"""
    df = get_latest_fund_data(fund_code)
    if df is None:
        return {"error": f"无法获取基金 {fund_code} 的数据。"}

    df_with_ma = calculate_moving_averages(df, fast_period=FAST_MA_PERIOD, slow_period=SLOW_MA_PERIOD)
    
    latest_data = df_with_ma.iloc[-1]
    previous_data = df_with_ma.iloc[-2]

    latest_date = latest_data.name.date()
    latest_close = latest_data['close']
    fast_ma = latest_data['fast_ma']
    slow_ma = latest_data['slow_ma']

    if pd.isna(fast_ma) or pd.isna(slow_ma):
        signal = "持有/观望"
        reason = "均线指标值无效，数据不足或计算错误，建议观望。"
    else:
        is_golden_cross = (previous_data['fast_ma'] < previous_data['slow_ma']) and (latest_data['fast_ma'] > latest_data['slow_ma'])
        is_death_cross = (previous_data['fast_ma'] > previous_data['slow_ma']) and (latest_data['fast_ma'] < latest_data['slow_ma'])

        if not is_holding:
            if is_golden_cross:
                signal = "买入"
                reason = f"均线出现金叉 (快线 {fast_ma:.4f} 上穿 慢线 {slow_ma:.4f})，是潜在的买入时机。"
            else:
                signal = "持有/观望"
                reason = f"快线 ({fast_ma:.4f}) 仍在慢线 ({slow_ma:.4f}) 下方，未形成金叉。"
        else: # is_holding is True
            if is_death_cross:
                signal = "卖出"
                reason = f"均线出现死叉 (快线 {fast_ma:.4f} 下穿 慢线 {slow_ma:.4f})，是潜在的卖出时机。"
            else:
                signal = "持有/观望" # 继续持有
                reason = f"快线 ({fast_ma:.4f}) 仍在慢线 ({slow_ma:.4f}) 上方，未形成死叉，继续持有。"

    return {
        "signal": signal,
        "reason": reason,
        "latest_date": latest_date,
        "latest_close": latest_close,
        "metrics": {
            "fast_ma_period": FAST_MA_PERIOD,
            "fast_ma_value": round(fast_ma, 4) if pd.notna(fast_ma) else None,
            "slow_ma_period": SLOW_MA_PERIOD,
            "slow_ma_value": round(slow_ma, 4) if pd.notna(slow_ma) else None,
        }
    }