#!/bin/sh
set -e

# 等待数据库就绪
python -m wechat_mqtt.db.wait_for_db

# 按需执行数据库迁移
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations ..."
    alembic upgrade head
fi

# 启动应用
exec python -m wechat_mqtt.main
