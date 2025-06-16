# src/python_cli_starter/main.py (修改后)

from fastapi import FastAPI, Depends, HTTPException
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

# 删除和修改的API端点也应在此处实现...
# @app.delete(...)
# @app.put(...)
