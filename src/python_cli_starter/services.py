# services.py
from . import models, schemas, data_fetcher
from sqlalchemy.orm import Session
from datetime import date, datetime
import pandas as pd
from typing import List, Optional, Dict, Any

# 自定义一个业务逻辑层面的异常，以便CLI和API可以分别处理
class HoldingExistsError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"基金代码 '{code}' 已存在。")

def create_new_holding(db: Session, holding_data: schemas.HoldingCreate) -> models.Holding:
    """
    创建新持仓。
    - 根据初始买入金额和当日净值计算出'持有份额'。
    - 同时获取并保存当前的实时估值信息。
    """
    # 1. 检查存在性 (不变)
    existing_holding = db.query(models.Holding).filter(models.Holding.code == holding_data.code).first()
    if existing_holding:
        raise HoldingExistsError(code=holding_data.code)

    # 2. 获取基金的名称和昨日净值 (不变)
    realtime_data = data_fetcher.fetch_fund_realtime_estimate(holding_data.code)
    
    # --- 名称和初始净值处理逻辑 (不变) ---
    final_name = ""
    yesterday_nav = 1.0 

    if realtime_data and 'name' in realtime_data and 'dwjz' in realtime_data:
        fund_name_from_api = realtime_data['name']
        try:
            yesterday_nav = float(realtime_data['dwjz'])
        except (ValueError, TypeError):
            print(f"警告：基金 {holding_data.code} 的昨日净值 '{realtime_data['dwjz']}' 无效。")
            realtime_data = None
    else:
        print(f"警告：无法从实时接口获取基金 {holding_data.code} 的详细信息。")

    if realtime_data:
        final_name = fund_name_from_api
    elif holding_data.name:
        final_name = holding_data.name
    else:
        raise ValueError(f"无法自动获取基金 {holding_data.code} 的名称，请通过 --name 参数手动提供。")
        
    if yesterday_nav <= 0:
        raise ValueError(f"无法为基金 {holding_data.code} 获取有效的初始净值。")

    # 3. 计算份额 (不变)
    initial_shares = holding_data.holding_amount / yesterday_nav

    # --- 4. 核心改动：准备并填充实时估值数据 ---
    estimate_nav = None
    estimate_amount = None
    change_pct = None
    update_time = None

    if realtime_data:
        try:
            estimate_nav = float(realtime_data.get('gsz'))
            change_pct = float(realtime_data.get('gszzl'))
            update_time_str = realtime_data.get('gztime')
            if update_time_str:
                update_time = datetime.fromisoformat(update_time_str)
            
            # 计算估算金额
            if estimate_nav is not None:
                estimate_amount = initial_shares * estimate_nav
        except (ValueError, TypeError) as e:
            print(f"处理基金 {holding_data.code} 的实时估值数据时出错: {e}")
            # 如果估值数据有问题，不影响主流程，保持为 None 即可

    # 5. 创建数据库模型实例，并填入所有字段
    db_holding = models.Holding(
        code=holding_data.code,
        name=final_name,
        shares=initial_shares,
        yesterday_nav=yesterday_nav,
        holding_amount=holding_data.holding_amount,
        
        # 填充实时估值字段
        today_estimate_nav=estimate_nav,
        today_estimate_amount=estimate_amount,
        percentage_change=change_pct,
        today_estimate_update_time=update_time
    )
    
    # 6. 提交到数据库 (不变)
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
    - 根据新的总金额和最新的实际净值，重新计算总份额。
    - 同时，立即获取并更新该基金的盘中估值数据。
    """
    # 1. 查找要更新的持仓记录 (不变)
    holding_to_update = db.query(models.Holding).filter(models.Holding.code == code).first()
    
    if not holding_to_update:
        raise HoldingNotFoundError(code=code)
    
    if holding_to_update.yesterday_nav <= 0:
        raise ValueError(f"基金 {code} 的昨日净值为零或无效，无法重新计算份额。")

    # 2. 核心计算：根据新的总金额和最新的实际净值，重新计算总份额 (不变)
    new_shares = new_amount / float(holding_to_update.yesterday_nav)

    # 3. 更新核心数据：金额和份额 (不变)
    holding_to_update.holding_amount = new_amount
    holding_to_update.shares = new_shares
    
    # --- 4. 核心改动：获取并更新实时估值数据 ---
    print(f"正在为基金 {code} 获取最新的盘中估值...")
    realtime_data = data_fetcher.fetch_fund_realtime_estimate(code)

    if realtime_data:
        try:
            # 解析所有估值相关数据
            estimate_nav = float(realtime_data.get('gsz'))
            change_pct = float(realtime_data.get('gszzl'))
            update_time_str = realtime_data.get('gztime')
            update_time = datetime.fromisoformat(update_time_str) if update_time_str else None
            
            # 使用新的份额计算估算金额
            estimate_amount = new_shares * estimate_nav if estimate_nav is not None else None

            # 将解析出的新数据更新到持仓对象上
            holding_to_update.today_estimate_nav = estimate_nav
            holding_to_update.today_estimate_amount = estimate_amount
            holding_to_update.percentage_change = change_pct
            holding_to_update.today_estimate_update_time = update_time
            
            print(f"已更新 {code} 的实时估值。")
        except (ValueError, TypeError) as e:
            print(f"处理基金 {code} 的实时估值数据时出错（更新操作期间）: {e}")
            # 即使估值获取失败，我们也要保证核心的金额和份额更新能被保存
            # 所以这里只打印错误，不抛出异常，让流程继续
    else:
        print(f"未能获取基金 {code} 的实时估值（更新操作期间）。")

    # 5. 提交所有更改到数据库
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

def get_history_with_ma(
    db: Session, 
    code: str, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None,
    ma_options: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    获取指定基金的历史净值，并计算指定的移动平均线。

    Args:
        db (Session): 数据库会话。
        code (str): 基金代码。
        start_date (Optional[date]): 查询开始日期。
        end_date (Optional[date]): 查询结束日期。
        ma_options (Optional[List[int]]): 需要计算的均线周期列表, e.g., [5, 10, 20]。

    Returns:
        pd.DataFrame: 包含净值和所选均线的数据框。
    """
    # 1. 构建基础查询
    query = db.query(models.NavHistory).filter(models.NavHistory.code == code)

    # 2. 根据日期参数筛选
    if start_date:
        query = query.filter(models.NavHistory.nav_date >= start_date)
    if end_date:
        query = query.filter(models.NavHistory.nav_date <= end_date)
    
    # 3. 按日期排序并执行查询
    history_records = query.order_by(models.NavHistory.nav_date.asc()).all()
    
    if not history_records:
        return pd.DataFrame() # 如果没有数据，返回一个空的 DataFrame

    # 4. 将查询结果转换为 Pandas DataFrame
    df = pd.DataFrame(
        [(record.nav_date, float(record.nav)) for record in history_records],
        columns=['date', 'nav']
    )
    df['date'] = pd.to_datetime(df['date'])
    
    # 5. 根据选项计算移动平均线
    if ma_options:
        for ma in ma_options:
            if isinstance(ma, int) and ma > 0:
                df[f'ma{ma}'] = df['nav'].rolling(window=ma).mean()

    return df

def export_holdings_data(db: Session) -> List[Dict[str, Any]]:
    """
    导出所有持仓数据。
    我们只导出核心数据：基金代码和持有份额。
    """
    holdings = db.query(models.Holding).all()
    
    # 构造一个只包含核心数据的列表
    export_data = [
        {
            "code": h.code,
            "shares": float(h.shares) # 将 Decimal 转换为 float 以便 JSON 序列化
        }
        for h in holdings
    ]
    return export_data

def import_holdings_data(db: Session, data_to_import: List[Dict[str, Any]], overwrite: bool = False):
    """
    导入持仓数据。

    Args:
        db (Session): 数据库会话。
        data_to_import (List[Dict[str, Any]]): 包含要导入数据的字典列表。
        overwrite (bool): 是否覆盖现有数据。如果为 True，将先删除所有现有持仓。
    
    Returns:
        A tuple (imported_count, skipped_count)
    """
    if overwrite:
        print("覆盖模式已启用，正在删除所有现有持仓数据...")
        db.query(models.NavHistory).delete()
        db.query(models.Holding).delete()
        # 注意：在覆盖模式下，我们不需要单独提交，因为后续操作在同一个事务中
    
    imported_count = 0
    skipped_count = 0
    
    for item in data_to_import:
        code = item.get("code")
        shares = item.get("shares")

        if not code or shares is None:
            print(f"跳过无效记录: {item}")
            skipped_count += 1
            continue
            
        # 检查是否已存在 (仅在非覆盖模式下)
        if not overwrite:
            existing = db.query(models.Holding).filter_by(code=code).first()
            if existing:
                print(f"基金 {code} 已存在，跳过导入。")
                skipped_count += 1
                continue
        
        # 获取基金的最新信息来填充其他字段
        realtime_data = data_fetcher.fetch_fund_realtime_estimate(code)
        if not realtime_data:
            print(f"无法获取基金 {code} 的信息，跳过导入。")
            skipped_count += 1
            continue
            
        name = realtime_data.get('name', 'N/A')
        yesterday_nav = float(realtime_data.get('dwjz', 0))
        
        if yesterday_nav <= 0:
            print(f"基金 {code} 的净值无效，跳过导入。")
            skipped_count += 1
            continue
            
        holding_amount = float(shares) * yesterday_nav
        
        new_holding = models.Holding(
            code=code,
            name=name,
            shares=float(shares),
            yesterday_nav=yesterday_nav,
            holding_amount=holding_amount
        )
        db.add(new_holding)
        imported_count += 1
        print(f"准备导入基金: {code}, 份额: {shares}")

    db.commit()
    return imported_count, skipped_count