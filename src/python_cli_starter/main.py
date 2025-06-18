# src/python_cli_starter/main.py (更新后)
from fastapi import FastAPI, Depends, HTTPException, Query, Response, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import logging

# 1. 导入新的日志配置和我们自己的模块
from .logger_config import setup_logging
from .scheduler import scheduler_runner
from . import models, crud, schemas, services
from .models import SessionLocal

# 2. 在应用启动前，最先配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 在应用启动时创建数据库表
models.create_db_and_tables()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时执行的代码
    logger.info("FastAPI 应用启动...")
    # 启动后台调度器
    scheduler_runner.start()
    
    yield # 这是应用运行的时间点
    
    # 在应用关闭时执行的代码
    logger.info("FastAPI 应用关闭...")
    # 停止后台调度器
    scheduler_runner.stop()

# 将FastAPI实例命名为 api_app，以示区分
api_app = FastAPI(title="基金投资助手 API", lifespan=lifespan)

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
    df = services.get_history_with_ma(
        db=db,
        code=fund_code,
        start_date=start_date,
        end_date=end_date,
        ma_options=ma
    )
    
    if df.empty:
        raise HTTPException(status_code=404, detail=f"未找到基金代码为 '{fund_code}' 的历史数据，或指定时间范围内无数据。")

    json_str = df.to_json(orient='records', date_format='iso', default_handler=None)
    return JSONResponse(content=json.loads(json_str))

# --- 3. 添加新的工具类路由 ---
@api_app.get("/utils/export", summary="导出所有持仓数据")
def export_data_endpoint(db: Session = Depends(get_db)):
    """
    将所有持仓的核心数据（代码和份额）导出为 JSON 文件。
    """
    export_data = services.export_holdings_data(db)
    
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=fund_holdings_export.json"
        }
    )

@api_app.post("/utils/import", summary="通过上传JSON文件导入持仓数据")
async def import_data_endpoint(
    db: Session = Depends(get_db),
    file: UploadFile = File(..., description="包含持仓数据的 JSON 文件"),
    overwrite: bool = Form(False, description="是否覆盖所有现有数据")
):
    """
    从上传的 JSON 文件中导入持仓数据。
    可以增量添加，也可以选择覆盖模式删除所有旧数据。
    """
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件格式必须是 JSON。")
        
    content = await file.read()
    try:
        data_to_import = json.loads(content)
        if not isinstance(data_to_import, list):
            raise ValueError("JSON content must be a list of objects.")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse uploaded JSON file: {e}")
        raise HTTPException(status_code=400, detail="JSON 文件内容无效或格式不正确。")
    
    try:
        imported, skipped = services.import_holdings_data(db, data_to_import, overwrite)
        return {"message": "导入完成", "imported": imported, "skipped": skipped}
    except Exception as e:
        logger.exception(f"An unexpected error occurred during the import process for file '{file.filename}'.")
        raise HTTPException(status_code=500, detail=f"导入过程中发生错误: {str(e)}")