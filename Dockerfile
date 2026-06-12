# 使用极轻量的 python 3.12 slim 镜像
FROM python:3.12-slim

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 避免生成 .pyc 并启用无缓冲输出（便于实时查看日志）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# 先安装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制源码、迁移配置与入口脚本
COPY src/ ./src/
COPY alembic.ini .
COPY migrations/ ./migrations/
COPY entrypoint.sh .
# 去除可能的 Windows 换行符并赋予执行权限
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# 创建非 root 用户并切换
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["./entrypoint.sh"]
