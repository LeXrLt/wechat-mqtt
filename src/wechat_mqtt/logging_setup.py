"""
日志配置模块
"""

import logging
import sys


def setup_logging(level: str = "DEBUG") -> None:
    """
    初始化全局日志配置。

    参数：
        level (str): 日志级别，如 DEBUG/INFO/WARNING/ERROR
    """
    log_level = getattr(logging, level.upper(), logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    # 避免重复添加 handler
    root.handlers.clear()
    root.addHandler(handler)
