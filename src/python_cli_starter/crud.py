from sqlalchemy.orm import Session
from fastapi import HTTPException
from . import models, schemas, services

def get_holding(db: Session, fund_code: str):
    """根据基金代码查询单个持仓"""
    return db.query(models.Holding).filter(models.Holding.code == fund_code).first()

def get_holdings(db: Session, skip: int = 0, limit: int = 100):
    """查询所有持仓记录，支持分页"""
    return db.query(models.Holding).offset(skip).limit(limit).all()

def create_holding(db: Session, holding: schemas.HoldingCreate) -> models.Holding:
    """
    (API层) 创建一个新的持仓记录。
    它会调用服务层的业务逻辑，并处理可能发生的业务异常。
    """
    try:
        # 调用服务层的核心逻辑
        new_holding = services.create_new_holding(db=db, holding_data=holding)
        return new_holding
    except services.HoldingExistsError as e:
        # 将业务逻辑异常 转换为 FastAPI 的 HTTP 异常
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        # 捕获其他可能的业务错误，例如获取数据失败
        raise HTTPException(status_code=404, detail=str(e))


def get_nav_history(db: Session, fund_code: str):
    """根据基金代码查询所有历史净值"""
    return db.query(models.NavHistory).filter(models.NavHistory.code == fund_code).order_by(models.NavHistory.nav_date).all()


def update_holding(db: Session, code: str, amount: float) -> models.Holding:
    """(API层) 更新持仓金额"""
    try:
        return services.update_holding_amount(db=db, code=code, new_amount=amount)
    except services.HoldingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

def delete_holding(db: Session, code: str):
    """(API层) 删除持仓记录"""
    try:
        services.delete_holding_by_code(db=db, code=code)
        # 成功删除后，API 通常返回一个 204 No Content 状态码，表示无内容返回
        # 我们可以在 main.py 中处理这个
    except services.HoldingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))