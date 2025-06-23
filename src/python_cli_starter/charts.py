# src/python_cli_starter/charts.py

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# --- RSI 策略默认参数 ---
RSI_PERIOD = 14
RSI_UPPER = 70.0
RSI_LOWER = 30.0

def get_historical_fund_data(fund_symbol: str, start_date: str) -> Optional[pd.DataFrame]:
    """获取指定基金从开始日期至今的全部历史净值数据。"""
    logger.info(f"[Charts] 正在为基金 {fund_symbol} 获取历史净值数据 (从 {start_date} 开始)...")
    try:
        fund_nav_df = ak.fund_open_fund_info_em(symbol=fund_symbol, indicator="单位净值走势")
        fund_nav_df['净值日期'] = pd.to_datetime(fund_nav_df['净值日期'])
        fund_nav_df = fund_nav_df.set_index('净值日期')
        fund_nav_df = fund_nav_df[['单位净值']]
        fund_nav_df.columns = ['close']
        fund_nav_df['close'] = pd.to_numeric(fund_nav_df['close'])
        
        fund_nav_df = fund_nav_df.sort_index(ascending=True)
        # 为了确保RSI计算的准确性，我们需要在开始日期前回溯一段数据
        # 比如多获取 2 * RSI_PERIOD 天的数据
        buffer_start_date = (pd.to_datetime(start_date) - timedelta(days=2 * RSI_PERIOD)).strftime('%Y-%m-%d')
        full_df = fund_nav_df[buffer_start_date:]

        if full_df.empty:
            logger.warning(f"获取基金 {fund_symbol} 数据为空。")
            return None
            
        logger.info(f"数据获取成功！共获取 {len(full_df)} 条记录。")
        return full_df
        
    except Exception as e:
        logger.error(f"获取基金 {fund_symbol} 数据时发生错误: {e}")
        return None

def calculate_rsi(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """计算 RSI 指标。"""
    delta = data['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period - 1, adjust=False).mean()
    ema_down = down.ewm(com=period - 1, adjust=False).mean()
    rs = ema_up / ema_down
    data['rsi'] = 100 - (100 / (1 + rs))
    return data

def generate_rsi_signals(data: pd.DataFrame) -> pd.DataFrame:
    """根据RSI指标生成买卖信号。"""
    signals = []
    position = 0
    data['prev_rsi'] = data['rsi'].shift(1)
    
    for i in range(RSI_PERIOD, len(data)):
        current_rsi = data['rsi'].iloc[i]
        prev_rsi = data['prev_rsi'].iloc[i]
        current_date = data.index[i]

        if pd.isna(current_rsi) or pd.isna(prev_rsi):
            continue

        if position == 0 and current_rsi <= RSI_LOWER and prev_rsi > RSI_LOWER:
            signals.append({'date': current_date, 'type': 'buy', 'rsi': current_rsi})
            position = 1
        elif position == 1 and current_rsi >= RSI_UPPER and prev_rsi < RSI_UPPER:
            signals.append({'date': current_date, 'type': 'sell', 'rsi': current_rsi})
            position = 0
    return pd.DataFrame(signals)

def get_rsi_chart_data(fund_code: str, start_date: str) -> Optional[Dict[str, Any]]:
    """
    为RSI策略生成 ECharts 所需的图表数据。
    """
    df_full = get_historical_fund_data(fund_code, start_date)
    if df_full is None:
        return None

    df_with_rsi = calculate_rsi(df_full, period=RSI_PERIOD)
    
    # 截取从 start_date 开始的最终数据用于显示
    df_display = df_with_rsi[start_date:].copy()

    if df_display.empty:
        return None

    signals_df = generate_rsi_signals(df_display)

    # 准备 ECharts 数据
    dates = df_display.index.strftime('%Y-%m-%d').tolist()
    rsi_values = df_display['rsi'].round(2).where(pd.notna(df_display['rsi']), None).tolist()
    net_values = df_display['close'].round(4).tolist()

    # 准备买卖信号点数据
    buy_signals = []
    sell_signals = []
    if not signals_df.empty:
        for _, row in signals_df.iterrows():
            signal_point = {
                'coord': [row['date'].strftime('%Y-%m-%d'), round(row['rsi'], 2)],
                'value': '买入' if row['type'] == 'buy' else '卖出'
            }
            if row['type'] == 'buy':
                buy_signals.append(signal_point)
            else:
                sell_signals.append(signal_point)

    return {
        "dates": dates,
        "netValues": net_values,
        "rsiValues": rsi_values,
        "signals": {
            "buy": buy_signals,
            "sell": sell_signals
        },
        "config": {
            "rsiPeriod": RSI_PERIOD,
            "rsiUpper": RSI_UPPER,
            "rsiLower": RSI_LOWER
        }
    }