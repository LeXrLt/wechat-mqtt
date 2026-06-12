"""
等待数据库就绪

容器启动时用于阻塞等待 PostgreSQL 可连接，避免迁移/应用过早启动。
"""

import logging
import sys
import time

from sqlalchemy import text

from wechat_mqtt.db.database import get_engine

logger = logging.getLogger("wait_for_db")


def wait_for_db(max_retries: int = 30, delay: float = 2.0) -> bool:
    """
    轮询尝试连接数据库，直至成功或超过最大重试次数。

    返回：
        bool: 连接成功返回 True，否则 False
    """
    engine = get_engine()
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.warning(f"等待数据库就绪 ({attempt}/{max_retries}): {e}")
            time.sleep(delay)
    logger.error("数据库连接失败，已达最大重试次数")
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not wait_for_db():
        sys.exit(1)
