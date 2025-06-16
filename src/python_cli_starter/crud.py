from sqlalchemy.orm import Session
from fastapi import HTTPException
from . import models, schemas

def get_holding(db: Session, fund_code: str):
    """根据基金代码查询单个持仓"""
    return db.query(models.Holding).filter(models.Holding.code == fund_code).first()

def get_holdings(db: Session, skip: int = 0, limit: int = 100):
    """查询所有持仓记录，支持分页"""
    return db.query(models.Holding).offset(skip).limit(limit).all()

def create_holding(db: Session, holding: schemas.HoldingCreate):
    """创建一个新的持仓记录"""
    # 1. 先检查该基金代码是否已存在
    db_holding = get_holding(db, fund_code=holding.code)
    if db_holding:
        # 如果已存在，则抛出 HTTP 400 错误
        raise HTTPException(status_code=400, detail=f"基金代码 '{holding.code}' 已存在。")

    # 2. 如果不存在，再执行创建逻辑
    # TODO: 从数据源获取真实的昨日净值
    yesterday_nav_mock = 1.0 

    db_holding = models.Holding(
        code=holding.code,
        name=holding.name,
        holding_amount=holding.holding_amount,
        yesterday_nav=yesterday_nav_mock 
    )
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    return db_holding

def get_nav_history(db: Session, fund_code: str):
    """根据基金代码查询所有历史净值"""
    return db.query(models.NavHistory).filter(models.NavHistory.code == fund_code).order_by(models.NavHistory.nav_date).all()

# 未来您可以在这里添加 update 和 delete 的函数
# def update_holding(...)
# def delete_holding(...)