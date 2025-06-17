# src/python_cli_starter/main.py (修改后)
# main.py
from fastapi import FastAPI, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from . import models, crud, schemas, services # 保持不变
from .models import SessionLocal
import json

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


@api_app.get("/holdings/{fund_code}/history")
def read_fund_history_with_ma(
    fund_code: str,
    start_date: Optional[date] = Query(None, description="查询开始日期 (格式: YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="查询结束日期 (格式: YYYY-MM-DD)"),
    ma: Optional[List[int]] = Query(None, description="需要计算的均线周期，可多选。例如: ma=5&ma=10&ma=20"),
    db: Session = Depends(get_db)
):
    """
    获取指定基金在特定时间范围内的历史净值及所选的移动平均线。
    """
    # 1. 调用服务层函数 (保持不变)
    df = services.get_history_with_ma(
        db=db,
        code=fund_code,
        start_date=start_date,
        end_date=end_date,
        ma_options=ma
    )
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"未找到基金代码为 '{fund_code}' 的历史数据，或指定时间范围内无数据。")

    # --- 核心改动在这里 ---
    # 2. 将 DataFrame 转换为 JSON 字符串，并让 pandas 处理 NaN
    #    `default_handler=None` 会将 NaN, NaT 等值转换为 null
    #    `orient='records'` 转换为字典列表格式
    #    我们还需要将日期格式化为 'YYYY-MM-DD' 字符串
    json_str = df.to_json(orient='records', date_format='iso', default_handler=None)
    
    # 3. 由于 to_json 返回的是字符串，我们需要先将其解析回 Python 对象
    #    这样 FastAPI 才能再次正确地将其序列化为 HTTP 响应
    #    或者，我们可以直接返回一个 JSONResponse
    
    # --- 方案A：返回 JSONResponse (更高效) ---
    return JSONResponse(content=json.loads(json_str))