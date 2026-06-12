"""
配置模块

通过环境变量读取配置，便于在 Docker 容器中部署。
"""

import os
from dataclasses import dataclass, field
from typing import List


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class MqttConfig:
    """MQTT 连接配置"""

    host: str = field(default_factory=lambda: _get_env("MQTT_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _get_int("MQTT_PORT", 1883))
    username: str = field(default_factory=lambda: _get_env("MQTT_USERNAME", ""))
    password: str = field(default_factory=lambda: _get_env("MQTT_PASSWORD", ""))
    client_id: str = field(
        default_factory=lambda: _get_env("MQTT_CLIENT_ID", "wechat-mqtt")
    )
    topic: str = field(
        default_factory=lambda: _get_env("MQTT_TOPIC", "wechat/messages")
    )
    keepalive: int = field(default_factory=lambda: _get_int("MQTT_KEEPALIVE", 60))
    qos: int = field(default_factory=lambda: _get_int("MQTT_QOS", 1))


@dataclass
class DatabaseConfig:
    """数据库连接配置（连接细节由 db.database 从环境变量读取）"""

    host: str = field(default_factory=lambda: _get_env("POSTGRES_HOST", "postgres"))
    port: int = field(default_factory=lambda: _get_int("POSTGRES_PORT", 5432))
    user: str = field(default_factory=lambda: _get_env("POSTGRES_USER", "wechat"))
    password: str = field(default_factory=lambda: _get_env("POSTGRES_PASSWORD", "wechat"))
    db: str = field(default_factory=lambda: _get_env("POSTGRES_DB", "wechat"))


@dataclass
class AppConfig:
    """应用全局配置"""

    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "DEBUG"))
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    # 启用的消息处理器名称列表，逗号分隔；为空则启用全部已注册处理器
    enabled_handlers: List[str] = field(
        default_factory=lambda: [
            h.strip()
            for h in _get_env("ENABLED_HANDLERS", "").split(",")
            if h.strip()
        ]
    )


def load_config() -> AppConfig:
    """加载应用配置。"""
    return AppConfig()
