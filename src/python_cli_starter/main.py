# src/python_cli_starter/main.py (修改后)
from fastapi import FastAPI, Depends, HTTPException, Query, Response, status, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
import inspect
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import logging

# 1. 导入新的日志配置和我们自己的模块
from .logger_config import setup_logging
# from .scheduler import scheduler_runner # <-- 移除导入
from . import models, crud, schemas, services
from .models import SessionLocal
from .strategies import STRATEGY_REGISTRY
from . import charts

# 2. 在应用启动前，最先配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 在应用启动时创建数据库表
models.create_db_and_tables()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时执行的代码
    logger.info("FastAPI 应用启动...")
    # 移除启动后台调度器的代码
    
    yield # 这是应用运行的时间点
    
    # 在应用关闭时执行的代码
    logger.info("FastAPI 应用关闭...")
    # 移除停止后台调度器的代码

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
    
@api_app.get(
    "/strategies/{strategy_name}/{fund_code}", 
    response_model=schemas.StrategySignal, 
    summary="获取基金策略信号"
)
def get_strategy_signal(
    strategy_name: str, 
    fund_code: str,
    is_holding: Optional[bool] = Query(None, description="【可选】对于需要持仓状态的策略，指定当前是否持有该基金。") # <-- 添加 is_holding 参数
):
    """
    根据指定的策略名称和基金代码，运行分析并返回交易信号。

    - **strategy_name**: 策略的简称 (例如: `rsi`, `bollinger_bands`)。
    - **fund_code**: 要分析的基金代码。
    - **is_holding**: (可选) 对于像布林带这样的策略，需要提供此参数 (`true`/`false`)。
    """
    logger.info(f"收到策略分析请求: strategy='{strategy_name}', code='{fund_code}', is_holding={is_holding}")

    strategy_function = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy_function:
        logger.warning(f"请求了未知的策略: '{strategy_name}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"策略 '{strategy_name}' 不存在。可用策略: {list(STRATEGY_REGISTRY.keys())}"
        )

    try:
        # --- 智能参数传递 ---
        # 检查策略函数需要哪些参数
        sig = inspect.signature(strategy_function)
        params = {}
        
        # 必须提供 fund_code
        if 'fund_code' in sig.parameters:
            params['fund_code'] = fund_code
        
        # 如果策略需要 is_holding，则传递它
        if 'is_holding' in sig.parameters:
            if is_holding is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"策略 '{strategy_name}' 需要 'is_holding' (true/false) 查询参数。"
                )
            params['is_holding'] = is_holding

        # 执行策略函数，并传入构造好的参数
        result_dict = strategy_function(**params)
        
        # (后续错误处理和响应封装保持不变)
        if result_dict.get("error"):
            error_message = result_dict["error"]
            logger.error(f"策略 '{strategy_name}' 执行失败: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )

        response_data = schemas.StrategySignal(
            fund_code=fund_code,
            strategy_name=strategy_name,
            **result_dict
        )
        return response_data

    except HTTPException as http_exc:
        # 重新抛出已知的HTTP异常
        raise http_exc
    except Exception as e:
        logger.exception(f"执行策略 '{strategy_name}' 时发生意外错误。")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行策略时发生内部错误: {str(e)}"
        )
    

@api_app.get(
    "/charts/rsi/{fund_code}",
    summary="获取RSI策略图表数据 (ECharts, 全部历史)",
    tags=["Charts"] # 使用 tags 对 API 进行分组
)
def get_rsi_chart_endpoint(fund_code: str):
    """
    获取指定基金的全部历史净值和RSI指标数据，
    返回格式适配 ECharts，用于绘制策略回测图。
    """
    logger.info(f"收到RSI图表数据请求 (全部历史): code='{fund_code}'")
    
    # 调用更新后的函数，不再传递 start_date
    chart_data = charts.get_rsi_chart_data(fund_code)
    
    if chart_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"无法为基金 {fund_code} 生成图表数据，请检查代码或确认该基金有历史数据。"
        )
        
    return chart_data