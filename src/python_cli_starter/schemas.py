# schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

class HoldingCreate(BaseModel):
    code: str
    name: str
    holding_amount: float

class Holding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    shares: float # Numeric 在 Pydantic 中通常映射为 float
    yesterday_nav: float
    holding_amount: float
    today_estimate_nav: Optional[float] = None
    today_estimate_amount: Optional[float] = None
    percentage_change: Optional[float] = None
    today_estimate_update_time: Optional[datetime] = None

class HoldingUpdate(BaseModel):
    holding_amount: float


class SignalType(str, Enum):
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有/观望"

class StrategySignal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fund_code: str
    strategy_name: str
    signal: SignalType
    reason: str
    latest_date: date
    latest_close: float
    metrics: Dict[str, Any]