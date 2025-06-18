# src/python_cli_starter/logger_config.py
import logging
import sys

def setup_logging():
    """
    配置全局日志记录器。
    """
    # 创建一个日志格式器
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 创建一个处理器，用于将日志记录输出到控制台
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    
    # 获取根日志记录器并添加处理器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # 设置全局日志级别为 INFO
    
    # 防止重复添加处理器
    if not root_logger.handlers:
        root_logger.addHandler(stream_handler)