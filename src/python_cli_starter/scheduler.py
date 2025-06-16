# src/python_cli_starter/scheduler.py

import schedule
import time
from .models import SessionLocal, Holding, NavHistory
# 引入我们之前编写的数据获取逻辑 (需要单独封装成函数)
from .data_fetcher import fetch_fund_history, fetch_fund_realtime_estimate 

def update_all_nav_history():
    """每日任务：更新所有持仓基金的历史净值"""
    print("开始执行每日任务：更新历史净值...")
    db = SessionLocal()
    try:
        holdings = db.query(Holding).all()
        for holding in holdings:
            print(f"正在更新基金 {holding.code} 的历史净值...")
            history_data = fetch_fund_history(holding.code) # fetch_fund_history需要您去实现
            # ... 在这里编写将 history_data 存入 NavHistory 表的逻辑 ...
            # 注意要去重，避免重复插入
        db.commit()
        print("历史净值更新完成。")
    except Exception as e:
        db.rollback()
        print(f"更新历史净值时发生错误: {e}")
    finally:
        db.close()

def update_today_estimate():
    """盘中任务：每半小时更新今日估值"""
    print("开始执行盘中任务：更新今日估值...")
    db = SessionLocal()
    try:
        holdings = db.query(Holding).all()
        for holding in holdings:
            realtime_data = fetch_fund_realtime_estimate(holding.code) # 这个函数也需要您实现
            if realtime_data and 'gsz' in realtime_data:
                holding.today_estimate_nav = float(realtime_data['gsz'])
                print(f"基金 {holding.code} 的估值更新为: {holding.today_estimate_nav}")
        db.commit()
        print("今日估值更新完成。")
    except Exception as e:
        db.rollback()
        print(f"更新今日估值时发生错误: {e}")
    finally:
        db.close()

def run_scheduler():
    """启动调度器"""
    # 每日凌晨1点执行历史数据更新
    schedule.every().day.at("01:00").do(update_all_nav_history)
    
    # 每个交易日的 09:30 到 15:00，每30分钟更新一次估值
    # (注意：这里的实现比较简单，未严格判断是否为交易日)
    for hour in range(9, 15):
        schedule.every().monday.at(f"{hour:02d}:30").do(update_today_estimate)
        schedule.every().tuesday.at(f"{hour:02d}:30").do(update_today_estimate)
        schedule.every().wednesday.at(f"{hour:02d}:30").do(update_today_estimate)
        schedule.every().thursday.at(f"{hour:02d}:30").do(update_today_estimate)
        schedule.every().friday.at(f"{hour:02d}:30").do(update_today_estimate)

    print("调度器已启动...")
    while True:
        schedule.run_pending()
        time.sleep(1)