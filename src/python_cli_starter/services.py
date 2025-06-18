# services.py
from . import models, schemas, data_fetcher
from sqlalchemy.orm import Session
from datetime import date, datetime
import pandas as pd
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class HoldingExistsError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"基金代码 '{code}' 已存在。")

def create_new_holding(db: Session, holding_data: schemas.HoldingCreate) -> models.Holding:
    """创建新持仓。"""
    logger.info(f"正在创建新的持仓记录, code: {holding_data.code}")
    existing_holding = db.query(models.Holding).filter(models.Holding.code == holding_data.code).first()
    if existing_holding:
        raise HoldingExistsError(code=holding_data.code)

    realtime_data = data_fetcher.fetch_fund_realtime_estimate(holding_data.code)
    
    final_name = ""
    yesterday_nav = 1.0 

    if realtime_data and 'name' in realtime_data and 'dwjz' in realtime_data:
        fund_name_from_api = realtime_data['name']
        try:
            yesterday_nav = float(realtime_data['dwjz'])
        except (ValueError, TypeError):
            logger.warning(f"基金 {holding_data.code} 的昨日净值 '{realtime_data['dwjz']}' 无效，将使用默认值。")
            realtime_data = None
    else:
        logger.warning(f"无法从实时接口获取基金 {holding_data.code} 的详细信息。")

    if realtime_data:
        final_name = fund_name_from_api
    elif holding_data.name:
        final_name = holding_data.name
    else:
        raise ValueError(f"无法自动获取基金 {holding_data.code} 的名称，请通过 --name 参数手动提供。")
        
    if yesterday_nav <= 0:
        raise ValueError(f"无法为基金 {holding_data.code} 获取有效的初始净值。")

    initial_shares = holding_data.holding_amount / yesterday_nav

    estimate_nav, estimate_amount, change_pct, update_time = None, None, None, None
    if realtime_data:
        try:
            estimate_nav = float(realtime_data.get('gsz'))
            change_pct = float(realtime_data.get('gszzl'))
            update_time_str = realtime_data.get('gztime')
            if update_time_str:
                update_time = datetime.fromisoformat(update_time_str)
            if estimate_nav is not None:
                estimate_amount = initial_shares * estimate_nav
        except (ValueError, TypeError) as e:
            logger.error(f"处理基金 {holding_data.code} 的实时估值数据时出错: {e}")

    db_holding = models.Holding(
        code=holding_data.code, name=final_name, shares=initial_shares,
        yesterday_nav=yesterday_nav, holding_amount=holding_data.holding_amount,
        today_estimate_nav=estimate_nav, today_estimate_amount=estimate_amount,
        percentage_change=change_pct, today_estimate_update_time=update_time
    )
    
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    logger.info(f"成功创建持仓: {db_holding.code}, 份额: {db_holding.shares:.4f}")
    return db_holding

class HoldingNotFoundError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"未找到基金代码为 '{code}' 的持仓记录。")

def update_holding_amount(db: Session, code: str, new_amount: float) -> models.Holding:
    """更新指定基金的持仓金额。"""
    logger.info(f"正在更新持仓金额, code: {code}, new_amount: {new_amount}")
    holding_to_update = db.query(models.Holding).filter(models.Holding.code == code).first()
    
    if not holding_to_update:
        raise HoldingNotFoundError(code=code)
    
    if holding_to_update.yesterday_nav <= 0:
        raise ValueError(f"基金 {code} 的昨日净值为零或无效，无法重新计算份额。")

    new_shares = new_amount / float(holding_to_update.yesterday_nav)
    holding_to_update.holding_amount = new_amount
    holding_to_update.shares = new_shares
    
    logger.info(f"正在为基金 {code} 获取最新的盘中估值...")
    realtime_data = data_fetcher.fetch_fund_realtime_estimate(code)
    if realtime_data:
        try:
            estimate_nav = float(realtime_data.get('gsz'))
            change_pct = float(realtime_data.get('gszzl'))
            update_time_str = realtime_data.get('gztime')
            update_time = datetime.fromisoformat(update_time_str) if update_time_str else None
            estimate_amount = new_shares * estimate_nav if estimate_nav is not None else None

            holding_to_update.today_estimate_nav = estimate_nav
            holding_to_update.today_estimate_amount = estimate_amount
            holding_to_update.percentage_change = change_pct
            holding_to_update.today_estimate_update_time = update_time
            logger.info(f"已更新 {code} 的实时估值。")
        except (ValueError, TypeError) as e:
            logger.error(f"处理基金 {code} 的实时估值数据时出错（更新操作期间）: {e}")
    else:
        logger.warning(f"未能获取基金 {code} 的实时估值（更新操作期间）。")

    db.commit()
    db.refresh(holding_to_update)
    logger.info(f"成功更新持仓: {code}, 新金额: {new_amount}, 新份额: {new_shares:.4f}")
    return holding_to_update

def delete_holding_by_code(db: Session, code: str):
    """根据基金代码删除一个持仓记录及其所有相关的历史净值数据。"""
    logger.info(f"准备删除基金 {code} 的所有记录。")
    holding_to_delete = db.query(models.Holding).filter(models.Holding.code == code).first()
    if not holding_to_delete:
        raise HoldingNotFoundError(code=code)
    
    db.query(models.NavHistory).filter(models.NavHistory.code == code).delete(synchronize_session=False)
    logger.info(f"已删除基金 {code} 的所有历史净值数据。")
    
    db.delete(holding_to_delete)
    db.commit()
    logger.info(f"已删除基金 {code} 的持仓记录。")

def get_history_with_ma(
    db: Session, code: str, start_date: Optional[date] = None, 
    end_date: Optional[date] = None, ma_options: Optional[List[int]] = None
) -> pd.DataFrame:
    """获取指定基金的历史净值，并计算指定的移动平均线。"""
    query = db.query(models.NavHistory).filter(models.NavHistory.code == code)
    if start_date:
        query = query.filter(models.NavHistory.nav_date >= start_date)
    if end_date:
        query = query.filter(models.NavHistory.nav_date <= end_date)
    
    history_records = query.order_by(models.NavHistory.nav_date.asc()).all()
    if not history_records:
        return pd.DataFrame()

    df = pd.DataFrame([(record.nav_date, float(record.nav)) for record in history_records], columns=['date', 'nav'])
    df['date'] = pd.to_datetime(df['date'])
    
    if ma_options:
        for ma in ma_options:
            if isinstance(ma, int) and ma > 0:
                df[f'ma{ma}'] = df['nav'].rolling(window=ma).mean()
    return df

def export_holdings_data(db: Session) -> List[Dict[str, Any]]:
    """导出所有持仓数据。"""
    logger.info("正在导出所有持仓的核心数据。")
    holdings = db.query(models.Holding).all()
    export_data = [{"code": h.code, "shares": float(h.shares)} for h in holdings]
    logger.info(f"成功准备了 {len(export_data)} 条持仓数据用于导出。")
    return export_data

def import_holdings_data(db: Session, data_to_import: List[Dict[str, Any]], overwrite: bool = False):
    """导入持仓数据。"""
    if overwrite:
        logger.info("覆盖模式已启用，正在删除所有现有持仓数据...")
        db.query(models.NavHistory).delete()
        db.query(models.Holding).delete()
        logger.info("所有旧数据已删除。")
    
    imported_count = 0
    skipped_count = 0
    
    for item in data_to_import:
        code = item.get("code")
        shares = item.get("shares")

        if not code or shares is None:
            logger.warning(f"跳过无效的导入记录: {item}")
            skipped_count += 1
            continue
            
        if not overwrite:
            existing = db.query(models.Holding).filter_by(code=code).first()
            if existing:
                logger.info(f"基金 {code} 已存在，跳过导入。")
                skipped_count += 1
                continue
        
        realtime_data = data_fetcher.fetch_fund_realtime_estimate(code)
        if not realtime_data:
            logger.warning(f"无法获取基金 {code} 的信息，跳过导入。")
            skipped_count += 1
            continue
            
        name = realtime_data.get('name', 'N/A')
        yesterday_nav = float(realtime_data.get('dwjz', 0))
        
        if yesterday_nav <= 0:
            logger.warning(f"基金 {code} 的净值无效，跳过导入。")
            skipped_count += 1
            continue
            
        holding_amount = float(shares) * yesterday_nav
        
        new_holding = models.Holding(
            code=code, name=name, shares=float(shares),
            yesterday_nav=yesterday_nav, holding_amount=holding_amount
        )
        db.add(new_holding)
        imported_count += 1
        logger.info(f"准备导入基金: {code}, 份额: {shares}")

    db.commit()
    logger.info(f"数据导入事务已提交。导入: {imported_count}, 跳过: {skipped_count}")
    return imported_count, skipped_count