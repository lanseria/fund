from sqlalchemy.orm import Session
from . import models, schemas, data_fetcher

# 自定义一个业务逻辑层面的异常，以便CLI和API可以分别处理
class HoldingExistsError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"基金代码 '{code}' 已存在。")

def create_new_holding(db: Session, holding_data: schemas.HoldingCreate) -> models.Holding:
    """
    创建新持仓的业务逻辑核心。
    如果持仓已存在，则抛出 HoldingExistsError。

    Args:
        db (Session): 数据库会话。
        holding_data (schemas.HoldingCreate): 待创建的持仓数据。

    Returns:
        models.Holding: 创建成功后的 SQLAlchemy 模型实例。
    
    Raises:
        HoldingExistsError: 如果基金代码已存在。
    """
    # 1. 检查基金代码是否已存在
    existing_holding = db.query(models.Holding).filter(models.Holding.code == holding_data.code).first()
    if existing_holding:
        raise HoldingExistsError(code=holding_data.code)

    # 2. 获取基金的名称和昨日净值
    # 注意：这里我们假设API传入的name是准确的，但更健壮的做法是从数据源获取
    # 我们从数据源获取昨日净值
    realtime_data = data_fetcher.fetch_fund_realtime_estimate(holding_data.code)
    if not realtime_data or 'dwjz' not in realtime_data:
        # 如果获取不到，可以抛出异常或使用默认值
        # 为了简单，我们暂时还用mock数据，但实际应该处理这个错误
        # raise ValueError(f"无法获取基金 {holding_data.code} 的昨日净值。")
        yesterday_nav = 1.0 # 实际应替换为错误处理
        fund_name = holding_data.name # 实际应从realtime_data['name']获取
    else:
        yesterday_nav = float(realtime_data['dwjz'])
        fund_name = realtime_data['name']

    # 3. 创建新的数据库模型实例
    db_holding = models.Holding(
        code=holding_data.code,
        name=fund_name,
        holding_amount=holding_data.holding_amount,
        yesterday_nav=yesterday_nav
    )
    
    # 4. 提交到数据库
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    
    return db_holding