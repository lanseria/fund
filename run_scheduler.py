# run_scheduler.py

import time
from src.python_cli_starter.scheduler import run_scheduler

if __name__ == "__main__":
    print("定时任务服务启动中...")
    try:
        # 调用我们已经写好的调度器启动函数
        run_scheduler()
    except Exception as e:
        print(f"定时任务服务启动失败: {e}")
        # 在容器环境中，如果启动失败，可以等待一段时间后退出，以便Docker可以重启
        time.sleep(60)
        exit(1)