# src/python_cli_starter/strategies/__init__.py

from . import rsi_strategy

# 策略注册表
# 键 (key) 是API路径中使用的名称 (例如 'rsi')
# 值 (value) 是策略模块中可执行的 run_strategy 函数
STRATEGY_REGISTRY = {
    "rsi": rsi_strategy.run_strategy,
}