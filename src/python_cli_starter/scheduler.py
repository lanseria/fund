# src/python_cli_starter/scheduler.py

import schedule
import time
import threading # 1. 导入 threading
from datetime import date, timedelta
from sqlalchemy import func

# 导入我们的模型、数据获取器等
from .models import SessionLocal, Holding, NavHistory
from .data_fetcher import fetch_fund_history, fetch_fund_realtime_estimate

def update_all_nav_history():
    """
    每日任务：增量更新所有持仓基金的历史净值。
    - 对每个持仓基金，找到其在数据库中最新的净值日期。
    - 只从数据源获取该日期之后的新数据，实现增量更新。
    - 批量插入新获取的数据，提高效率。
    """
    print("开始执行每日任务：更新历史净值...")
    db = SessionLocal()
    try:
        # 1. 获取所有持仓基金
        holdings = db.query(Holding).all()
        if not holdings:
            print("没有持仓基金，任务结束。")
            return

        for holding in holdings:
            print(f"--- 正在处理基金: {holding.name} ({holding.code}) ---")
            
            # 2. 查找该基金在数据库中最新的净值日期
            latest_date_in_db = db.query(func.max(NavHistory.nav_date)).filter(NavHistory.code == holding.code).scalar()

            start_date_to_fetch = None
            if latest_date_in_db:
                # 如果数据库中有数据，则从最新日期的后一天开始获取
                start_date_to_fetch = (latest_date_in_db + timedelta(days=1)).strftime('%Y-%m-%d')
                print(f"数据库中最新净值日期为: {latest_date_in_db}，将从 {start_date_to_fetch} 开始获取新数据。")
            else:
                # 如果数据库中没有该基金的任何数据，则获取全部历史数据
                print("数据库中无此基金历史数据，将获取全部历史。")

            # 3. 从数据源获取历史数据 (全量或增量)
            # 注意：天天基金的接口可能不严格遵守 start_date，所以我们获取后还需要自己过滤
            history_data_raw = fetch_fund_history(holding.code, start_date=start_date_to_fetch)

            if not history_data_raw:
                print(f"未能获取到基金 {holding.code} 的新历史数据。")
                continue

            # 4. 处理并批量插入新数据
            new_nav_records = []
            for record in history_data_raw:
                nav_date = date.fromisoformat(record['FSRQ'])
                
                # 再次确认日期是我们需要的，以防接口返回了旧数据
                if latest_date_in_db and nav_date <= latest_date_in_db:
                    continue
                    
                # 检查日涨跌幅是否为有效数字，如果不是则跳过（例如新基金、停牌等情况）
                try:
                    # 'JZZZL' 字段是日涨跌幅
                    float(record['JZZZL']) 
                except (ValueError, TypeError):
                    print(f"跳过无效记录: 日期 {nav_date}, 净值 {record['DWJZ']}, 涨跌幅 {record['JZZZL']}")
                    continue

                new_nav_records.append(
                    NavHistory(
                        code=holding.code,
                        nav_date=nav_date,
                        nav=float(record['DWJZ'])
                    )
                )

            if not new_nav_records:
                print("没有新的净值记录需要添加。")
                continue

            # 5. 使用 add_all 进行批量插入
            print(f"发现 {len(new_nav_records)} 条新净值记录，正在批量插入数据库...")
            db.add_all(new_nav_records)
            db.commit() # 在每个基金处理完后提交一次，避免单个基金失败影响全部
            print(f"基金 {holding.code} 的历史净值更新成功！")
            
            # 短暂休眠，避免请求过于频繁
            time.sleep(1) 

        print("\n所有基金的历史净值更新任务已全部完成。")

    except Exception as e:
        db.rollback() # 如果在循环中发生意外错误，回滚当前未提交的事务
        print(f"更新历史净值时发生严重错误: {e}")
    finally:
        db.close()

def update_today_estimate():
    """盘中任务：每半小时更新今日估值"""
    # ... 此函数保持不变 ...
    print("开始执行盘中任务：更新今日估值...")
    db = SessionLocal()
    try:
        holdings = db.query(Holding).all()
        for holding in holdings:
            realtime_data = fetch_fund_realtime_estimate(holding.code)
            if realtime_data and 'gsz' in realtime_data:
                # 找到对应的持仓对象并更新
                holding_to_update = db.query(Holding).filter(Holding.code == holding.code).first()
                if holding_to_update:
                    holding_to_update.today_estimate_nav = float(realtime_data['gsz'])
                    print(f"基金 {holding.code} 的估值更新为: {holding_to_update.today_estimate_nav}")
        db.commit()
        print("今日估值更新完成。")
    except Exception as e:
        db.rollback()
        print(f"更新今日估值时发生错误: {e}")
    finally:
        db.close()


# --- 2. 创建一个新的运行器类 ---
class SchedulerRunner:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._setup_schedule()

    def _setup_schedule(self):
        """配置所有的定时任务"""
        print("配置定时任务...")
        schedule.every().day.at("02:00").do(update_all_nav_history)
        
        for hour in range(9, 15):
            schedule.every().monday.at(f"{hour:02d}:30").do(update_today_estimate)
            schedule.every().tuesday.at(f"{hour:02d}:30").do(update_today_estimate)
            schedule.every().wednesday.at(f"{hour:02d}:30").do(update_today_estimate)
            schedule.every().thursday.at(f"{hour:02d}:30").do(update_today_estimate)
            schedule.every().friday.at(f"{hour:02d}:30").do(update_today_estimate)

    def _run_continuously(self):
        """在一个循环中运行所有待处理的任务，直到停止事件被设置"""
        print("调度器线程已启动，等待执行任务...")
        
        # 首次启动，立即执行一次历史数据更新
        print("首次启动，立即执行一次历史净值更新任务...")
        update_all_nav_history()
        
        while not self._stop_event.is_set():
            schedule.run_pending()
            # 休眠1秒，避免CPU空转，同时让停止事件可以被快速响应
            time.sleep(1)
        
        print("调度器线程已接收到停止信号，正在退出。")

    def start(self):
        """在后台线程中启动调度器"""
        if self._thread is None or not self._thread.is_alive():
            print("启动后台调度器线程...")
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_continuously)
            self._thread.daemon = True  # 设置为守护线程，主程序退出时它也会退出
            self._thread.start()

    def stop(self):
        """停止调度器线程"""
        if self._thread and self._thread.is_alive():
            print("正在发送停止信号给调度器线程...")
            self._stop_event.set()
            self._thread.join(timeout=5) # 等待线程最多5秒钟
            if self._thread.is_alive():
                print("警告：调度器线程未在5秒内正常停止。")

# 创建一个全局的调度器实例
scheduler_runner = SchedulerRunner()