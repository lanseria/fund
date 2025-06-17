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
    增强了对无法获取实时数据的基金的处理能力。
    """
    # 1. 检查基金代码是否已存在
    existing_holding = db.query(models.Holding).filter(models.Holding.code == holding_data.code).first()
    if existing_holding:
        raise HoldingExistsError(code=holding_data.code)

    # 2. 尝试从数据源获取基金的名称和昨日净值
    realtime_data = data_fetcher.fetch_fund_realtime_estimate(holding_data.code)
    
    fund_name = ""
    yesterday_nav = 1.0  # 设置一个安全的默认值

    if realtime_data and 'name' in realtime_data and 'dwjz' in realtime_data:
        # 成功获取到数据
        fund_name = realtime_data['name']
        try:
            yesterday_nav = float(realtime_data['dwjz'])
        except (ValueError, TypeError):
            # 如果昨日净值不是有效数字，也视为获取失败
            print(f"警告：基金 {holding_data.code} 的昨日净值 '{realtime_data['dwjz']}' 无效，将使用默认值。")
            realtime_data = None # 将其置为None，以便走下面的逻辑
    else:
        # 未能获取到有效数据
        print(f"警告：无法从实时接口获取基金 {holding_data.code} 的详细信息。")

    # 3. 决定基金名称
    if realtime_data:
        # 如果从API获取到，则使用API的名称（最准确）
        final_name = fund_name
    elif holding_data.name:
        # 如果API获取失败，但用户提供了名称，则使用用户提供的
        final_name = holding_data.name
        print(f"将使用您提供的名称: '{final_name}'")
    else:
        # 如果API获取失败，用户也没提供名称，则无法继续
        raise ValueError(f"无法自动获取基金 {holding_data.code} 的名称，请通过 --name 参数手动提供。")

    # 4. 创建新的数据库模型实例
    db_holding = models.Holding(
        code=holding_data.code,
        name=final_name,
        holding_amount=holding_data.holding_amount,
        yesterday_nav=yesterday_nav # 使用获取到的或默认的昨日净值
    )
    
    # 5. 提交到数据库
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    
    return db_holding


class HoldingNotFoundError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"未找到基金代码为 '{code}' 的持仓记录。")

def update_holding_amount(db: Session, code: str, new_amount: float) -> models.Holding:
    """
    更新指定基金的持仓金额。

    Raises:
        HoldingNotFoundError: 如果未找到指定代码的基金。
    """
    # 1. 查找要更新的持仓记录
    holding_to_update = db.query(models.Holding).filter(models.Holding.code == code).first()
    
    if not holding_to_update:
        raise HoldingNotFoundError(code=code)
    
    # 2. 更新金额
    holding_to_update.holding_amount = new_amount
    
    # 3. 提交更改
    db.commit()
    db.refresh(holding_to_update)
    
    return holding_to_update

def delete_holding_by_code(db: Session, code: str):
    """
    根据基金代码删除一个持仓记录及其所有相关的历史净值数据。

    Raises:
        HoldingNotFoundError: 如果未找到指定代码的基金。
    """
    # 1. 查找要删除的持仓记录
    holding_to_delete = db.query(models.Holding).filter(models.Holding.code == code).first()
    
    if not holding_to_delete:
        raise HoldingNotFoundError(code=code)
    
    # 2. 删除该基金的所有历史净值数据 (级联删除)
    db.query(models.NavHistory).filter(models.NavHistory.code == code).delete(synchronize_session=False)
    
    # 3. 删除持仓记录本身
    db.delete(holding_to_delete)
    
    # 4. 提交事务
    db.commit()
    
    # 删除操作成功，无需返回对象