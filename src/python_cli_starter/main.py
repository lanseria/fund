# src/python_cli_starter/main.py (修改后)

from fastapi import FastAPI, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
import pandas as pd

from . import models, crud, schemas # 保持不变
from .models import SessionLocal, engine # 保持不变

# 在应用启动时创建数据库表
models.create_db_and_tables()

# 将FastAPI实例命名为 api_app，以示区分
api_app = FastAPI(title="基金投资助手 API")

# Dependency: 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API 路由定义 (保持不变) ---
@api_app.get("/holdings/", response_model=list[schemas.Holding])
def read_holdings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    holdings = crud.get_holdings(db, skip=skip, limit=limit)
    return holdings

@api_app.post("/holdings/", response_model=schemas.Holding)
def create_holding(holding: schemas.HoldingCreate, db: Session = Depends(get_db)):
    return crud.create_holding(db=db, holding=holding)

# 创建一个 Pydantic 模型用于接收更新请求的数据
class HoldingUpdate(schemas.BaseModel):
    holding_amount: float

@api_app.put("/holdings/{fund_code}", response_model=schemas.Holding)
def update_holding_endpoint(fund_code: str, holding_update: HoldingUpdate, db: Session = Depends(get_db)):
    """
    更新指定基金代码的持仓金额。
    """
    return crud.update_holding(db=db, code=fund_code, amount=holding_update.holding_amount)


@api_app.delete("/holdings/{fund_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holding_endpoint(fund_code: str, db: Session = Depends(get_db)):
    """
    删除指定基金代码的持仓记录及其所有历史数据。
    """
    crud.delete_holding(db=db, code=fund_code)
    # 成功时返回 204 No Content，不需要响应体
    return Response(status_code=status.HTTP_204_NO_CONTENT)