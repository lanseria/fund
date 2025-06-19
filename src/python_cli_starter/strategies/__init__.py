# src/python_cli_starter/strategies/__init__.py

from . import rsi_strategy
from . import bollinger_bands_strategy # <-- 1. 导入新策略模块

# 策略注册表
# 键 (key) 是API路径中使用的名称
# 值 (value) 是策略模块中可执行的 run_strategy 函数
STRATEGY_REGISTRY = {
    "rsi": rsi_strategy.run_strategy,
    "bollinger_bands": bollinger_bands_strategy.run_strategy, # <-- 2. 添加新策略到注册表
}