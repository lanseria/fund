# src/python_cli_starter/scheduler.py
import schedule
import time
import threading
from datetime import date, timedelta, datetime
from sqlalchemy import func
import logging

from .models import SessionLocal, Holding, NavHistory
from .data_fetcher import fetch_fund_history, fetch_fund_realtime_estimate

logger = logging.getLogger(__name__)

def update_all_nav_history():
    """每日任务：增量更新所有持仓基金的历史净值，并校准持仓金额。"""
    logger.info("开始执行每日任务：更新历史净值与持仓金额校准...")
    db = SessionLocal()
    try:
        holdings = db.query(Holding).all()
        if not holdings:
            logger.info("没有持仓基金，任务结束。")
            return

        for holding in holdings:
            logger.info(f"--- 正在处理基金: {holding.name} ({holding.code}) ---")
            
            latest_date_in_db = db.query(func.max(NavHistory.nav_date)).filter(NavHistory.code == holding.code).scalar()
            start_date_to_fetch = None
            if latest_date_in_db:
                start_date_to_fetch = (latest_date_in_db + timedelta(days=1)).strftime('%Y-%m-%d')
                logger.info(f"数据库中最新净值日期为: {latest_date_in_db}，将从 {start_date_to_fetch} 开始获取新数据。")
            else:
                logger.info("数据库中无此基金历史数据，将获取全部历史。")

            history_data_raw = fetch_fund_history(holding.code, start_date=start_date_to_fetch)
            if not history_data_raw:
                logger.warning(f"未能获取到基金 {holding.code} 的新历史数据。")
                continue

            new_nav_records = []
            for record in history_data_raw:
                nav_date = date.fromisoformat(record['FSRQ'])
                if latest_date_in_db and nav_date <= latest_date_in_db:
                    continue
                try:
                    float(record['JZZZL']) 
                except (ValueError, TypeError):
                    logger.warning(f"跳过无效记录: 基金 {holding.code}, 日期 {nav_date}, 净值 {record['DWJZ']}, 涨跌幅 {record['JZZZL']}")
                    continue
                new_nav_records.append(NavHistory(code=holding.code, nav_date=nav_date, nav=float(record['DWJZ'])))

            if not new_nav_records:
                logger.info(f"基金 {holding.code} 没有新的净值记录需要添加。")
                continue

            logger.info(f"发现 {len(new_nav_records)} 条新净值记录，正在批量插入数据库...")
            db.add_all(new_nav_records)
            db.commit()
            logger.info(f"基金 {holding.code} 的历史净值更新成功！")
            time.sleep(1)
            
            latest_nav_record = db.query(NavHistory).filter(NavHistory.code == holding.code).order_by(NavHistory.nav_date.desc()).first()
            if latest_nav_record:
                latest_actual_nav = float(latest_nav_record.nav)
                new_holding_amount = float(holding.shares) * latest_actual_nav
                holding.holding_amount = new_holding_amount
                holding.yesterday_nav = latest_actual_nav
                logger.info(f"基金 {holding.code} 的持仓已校准：最新净值 {latest_actual_nav}, 最新金额 {new_holding_amount:.2f}")

        db.commit()
        logger.info("\n所有基金的历史净值更新与持仓金额校准任务已全部完成。")
    except Exception as e:
        db.rollback()
        logger.exception("更新历史净值时发生严重错误。")
    finally:
        db.close()

def update_today_estimate():
    """盘中任务：更新今日估值、估算金额、涨跌幅和更新时间。"""
    logger.info("开始执行盘中任务：更新今日估值...")
    db = SessionLocal()
    try:
        holdings = db.query(Holding).all()
        for holding in holdings:
            realtime_data = fetch_fund_realtime_estimate(holding.code)
            if realtime_data and 'gsz' in realtime_data:
                try:
                    estimate_nav = float(realtime_data['gsz'])
                    change_pct = float(realtime_data['gszzl'])
                    update_time_str = realtime_data['gztime']
                    update_time = datetime.fromisoformat(update_time_str)
                    estimate_amount = float(holding.shares) * estimate_nav

                    holding.today_estimate_nav = estimate_nav
                    holding.percentage_change = change_pct
                    holding.today_estimate_update_time = update_time
                    holding.today_estimate_amount = estimate_amount
                    logger.info(f"基金 {holding.code} 已更新，估值: {estimate_nav}, 估算金额: {estimate_amount:.2f}")
                except (ValueError, TypeError) as e:
                    logger.error(f"处理基金 {holding.code} 的实时数据时出错: {e}")
        
        db.commit()
        logger.info("今日估值更新完成。")
    except Exception as e:
        db.rollback()
        logger.exception("更新今日估值时发生错误。")
    finally:
        db.close()

class SchedulerRunner:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._setup_schedule()

    def _setup_schedule(self):
        """配置所有的定时任务 (优化后)。"""
        logger.info("正在配置定时任务...")
        
        # 每日净值同步任务
        schedule.every().day.at("02:00").do(update_all_nav_history)
        
        # --- 代码优化：使用循环配置周一到周五的盘中任务 ---
        weekdays = [
            schedule.every().monday, schedule.every().tuesday, 
            schedule.every().wednesday, schedule.every().thursday, 
            schedule.every().friday
        ]
        
        # 交易时间从 9 点到 14 点 (不含15点)
        for hour in range(9, 15):
            for day in weekdays:
                # 在每个小时的30分执行
                day.at(f"{hour:02d}:30").do(update_today_estimate)
        
        logger.info("所有定时任务配置完成。")

    def _run_continuously(self):
        """在一个循环中运行所有待处理的任务，直到停止事件被设置。"""
        logger.info("调度器线程已启动，等待执行任务...")
        
        logger.info("首次启动，立即执行一次历史净值更新任务...")
        try:
            update_all_nav_history()
        except Exception:
            logger.exception("首次启动执行历史净值更新任务失败。")
        
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("调度器线程已接收到停止信号，正在退出。")

    def start(self):
        """在后台线程中启动调度器。"""
        if self._thread is None or not self._thread.is_alive():
            logger.info("启动后台调度器线程...")
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_continuously)
            self._thread.daemon = True
            self._thread.start()

    def stop(self):
        """停止调度器线程。"""
        if self._thread and self._thread.is_alive():
            logger.info("正在发送停止信号给调度器线程...")
            self._stop_event.set()
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("警告：调度器线程未在5秒内正常停止。")

scheduler_runner = SchedulerRunner()