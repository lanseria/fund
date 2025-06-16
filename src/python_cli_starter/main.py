# src/python_cli_starter/main.py (修改后)

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd

from . import models, crud, schemas # 我们需要新建 crud.py 和 schemas.py
from .models import SessionLocal, engine

# 在应用启动时创建数据库表
models.create_db_and_tables()

app = FastAPI(title="基金投资助手 API")

# Dependency: 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/holdings/", response_model=list[schemas.Holding])
def read_holdings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """查询我的所有持仓基金"""
    holdings = crud.get_holdings(db, skip=skip, limit=limit)
    return holdings

@app.get("/holdings/{fund_code}/history")
def read_fund_history(fund_code: str, db: Session = Depends(get_db)):
    """查看具体基金的历史净值数据以及均线"""
    history = crud.get_nav_history(db, fund_code=fund_code)
    if not history:
        raise HTTPException(status_code=404, detail="未找到该基金的历史数据")
    
    # 使用pandas计算均线
    df = pd.DataFrame([(h.nav_date, float(h.nav)) for h in history], columns=['date', 'nav'])
    df = df.sort_values(by='date').reset_index(drop=True)
    
    df['ma5'] = df['nav'].rolling(window=5).mean()
    df['ma10'] = df['nav'].rolling(window=10).mean()
    df['ma20'] = df['nav'].rolling(window=20).mean()
    
    # 将NaN替换为None以便JSON序列化
    df = df.where(pd.notnull(df), None)
    
    return df.to_dict(orient='records')

@app.post("/holdings/", response_model=schemas.Holding)
def create_holding(holding: schemas.HoldingCreate, db: Session = Depends(get_db)):
    """添加我持有的基金"""
    return crud.create_holding(db=db, holding=holding)

# 删除和修改的API端点也应在此处实现...
# @app.delete(...)
# @app.put(...)

# 如果你想保留CLI功能，可以这样做
from .cli import app as cli_app

app.mount("/cli", cli_app) # 这是一个示例，通常API和CLI会分开运行