from pydantic import BaseModel
from typing import Optional

# 用于创建新持仓时，API接收的数据模型
class HoldingCreate(BaseModel):
    code: str
    name: str
    holding_amount: float

# 用于API响应，从数据库读取数据后返回给前端的模型
class Holding(BaseModel):
    code: str
    name: str
    yesterday_nav: float
    holding_amount: float
    today_estimate_nav: Optional[float] = None

    # 这个配置项允许Pydantic模型从ORM对象（如SQLAlchemy模型）中读取数据
    class Config:
        from_attributes = True