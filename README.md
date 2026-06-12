# wechat-mqtt

接收 [wechat-listener](../wechat-listener) 通过 MQTT 推送的微信消息，并进行处理与存储。

当前实现：实时接收 MQTT 消息、输出 DEBUG 日志、持久化到 PostgreSQL（含 pgvector 语义搜索能力）。架构设计便于后续扩展更多消息处理逻辑与 agent skill。

## 📦 项目结构

```
wechat-mqtt/
├── Dockerfile              # python:3.12-slim 轻量镜像
├── docker-compose.yml      # 容器编排（restart: unless-stopped, 非 root, 上海时区）
├── requirements.txt        # 依赖（paho-mqtt, SQLAlchemy, alembic, pgvector）
├── .env.example            # 环境变量示例
├── alembic.ini             # Alembic 迁移配置
├── migrations/             # 数据库迁移脚本
└── src/
    └── wechat_mqtt/
        ├── main.py         # 应用入口
        ├── config.py       # 环境变量配置
        ├── logging_setup.py# 日志配置
        ├── models.py       # 消息数据模型（DTO）
        ├── mqtt_client.py  # MQTT 监听客户端
        ├── db/             # 数据库模块
        │   ├── database.py # engine/session
        │   ├── models.py   # ORM 表模型
        │   ├── repository.py   # 数据访问层
        │   └── wait_for_db.py  # 启动等待数据库
        └── handlers/       # 消息处理器（可扩展）
            ├── base.py     # 处理器基类
            ├── registry.py # 处理器注册与分发
            ├── debug_handler.py   # 调试日志处理器
            └── persist_handler.py # 持久化到数据库
```

## 🚀 快速开始（Docker）

```bash
# 1. 复制环境变量并填写 MQTT 连接信息
cp .env.example .env

# 2. 构建并启动（自动拉起 postgres + adminer + wechat-mqtt，并执行迁移）
docker compose --env-file .env up -d --build

# 3. 查看实时日志
docker compose logs -f wechat-mqtt
```

启动后访问 **Adminer** 查看数据库：`http://localhost:8080`
（系统 PostgreSQL，服务器 `postgres`，用户/密码/库见 `.env`）

## 🔧 配置

所有配置通过环境变量传入，详见 `.env.example`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LOG_LEVEL` | 日志级别 | `DEBUG` |
| `MQTT_HOST` | MQTT broker 地址 | `127.0.0.1` |
| `MQTT_PORT` | MQTT 端口 | `1883` |
| `MQTT_USERNAME` | MQTT 用户名 | - |
| `MQTT_PASSWORD` | MQTT 密码 | - |
| `MQTT_TOPIC` | 订阅主题 | `wechat/messages` |
| `ENABLED_HANDLERS` | 启用的处理器（逗号分隔），空为全部 | - |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 数据库账号信息 | `wechat` |
| `EMBEDDING_DIM` | 语义向量维度 | `1536` |
| `RUN_MIGRATIONS` | 启动时自动执行迁移 | `true` |
| `ADMINER_PORT` | Adminer Web 端口 | `8080` |

> ⚠️ MQTT 连接信息需与 `wechat-listener` 的 `config.yaml` 中 `mqtt` 段一致。

## 🧩 扩展新的消息处理器

1. 在 `src/wechat_mqtt/handlers/` 下新建处理器文件，继承 `BaseHandler`：

```python
from wechat_mqtt.handlers.base import BaseHandler
from wechat_mqtt.models import WechatMessage


class MyHandler(BaseHandler):
    name = "my-handler"
    priority = 500

    def handle(self, message: WechatMessage) -> None:
        # 你的处理逻辑
        ...
```

2. 在 `handlers/registry.py` 的 `ALL_HANDLERS` 列表中注册该处理器。

3. （可选）通过 `ENABLED_HANDLERS` 环境变量控制启用哪些处理器。

## 📨 消息格式

来自 `wechat-listener` 的 `push-msg-to-mqtt-plugin`，JSON 结构：

```json
{
  "room_name": "群名称",
  "speaker_name": "发送人",
  "content": "消息内容",
  "is_bot": false,
  "msg_type": "Text",
  "timestamp": "...",
  "time_str": "..."
}
```

## 🔁 数据库迁移

使用 Alembic 管理表结构变更，迁移脚本位于 `migrations/`。

```bash
# 容器内（或本地设置好 PYTHONPATH 与数据库连接后）执行：
alembic upgrade head           # 升级到最新
alembic revision --autogenerate -m "add xxx"   # 修改 ORM 后生成新迁移
alembic downgrade -1           # 回滚一步
```

容器启动时若 `RUN_MIGRATIONS=true`（默认），会在等待数据库就绪后自动执行 `alembic upgrade head`。

## 🐍 本地运行（开发）

```bash
pip install -r requirements.txt
set PYTHONPATH=src        # Windows
export PYTHONPATH=src     # Linux/macOS
python -m wechat_mqtt.main
```
