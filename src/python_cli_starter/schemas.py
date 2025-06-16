from pydantic import BaseModel, ConfigDict
from typing import Optional

# 用于创建新持仓时，API接收的数据模型
class HoldingCreate(BaseModel):
    code: str
    name: str
    holding_amount: float

# 用于API响应，从数据库读取数据后返回给前端的模型
class Holding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    yesterday_nav: float
    holding_amount: float
    today_estimate_nav: Optional[float] = None