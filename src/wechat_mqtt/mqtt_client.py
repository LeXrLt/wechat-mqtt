"""
MQTT 客户端

负责连接 MQTT broker、订阅主题、接收消息并交由处理器注册表分发。
"""

import json
import logging

import paho.mqtt.client as mqtt

from wechat_mqtt.config import MqttConfig
from wechat_mqtt.handlers.registry import HandlerRegistry
from wechat_mqtt.models import WechatMessage

logger = logging.getLogger(__name__)


class MqttListener:
    """
    MQTT 监听器：连接 broker，订阅主题，解析消息并分发到处理器。
    """

    def __init__(self, config: MqttConfig, registry: HandlerRegistry) -> None:
        self.config = config
        self.registry = registry
        self.client = mqtt.Client(client_id=config.client_id)

        if config.username and config.password:
            self.client.username_pw_set(config.username, config.password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(
                f"已连接到 MQTT broker {self.config.host}:{self.config.port}，"
                f"订阅主题: {self.config.topic}"
            )
            client.subscribe(self.config.topic, qos=self.config.qos)
        else:
            logger.error(f"MQTT 连接失败，返回码: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"MQTT 意外断开，返回码: {rc}，将自动重连")

    def _on_message(self, client, userdata, msg):
        try:
            raw = msg.payload.decode("utf-8")
        except Exception as e:
            logger.error(f"消息解码失败: {e}")
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"收到非 JSON 消息，原文: {raw}")
            return

        message = WechatMessage.from_payload(payload)
        self.registry.dispatch(message)

    def run_forever(self) -> None:
        """连接 broker 并阻塞监听消息。"""
        logger.info(
            f"正在连接 MQTT broker {self.config.host}:{self.config.port} ..."
        )
        # 断线自动重连
        self.client.reconnect_delay_set(min_delay=1, max_delay=60)
        self.client.connect(
            self.config.host, self.config.port, keepalive=self.config.keepalive
        )
        self.client.loop_forever()

    def stop(self) -> None:
        """停止监听并断开连接。"""
        self.client.disconnect()
        logger.info("MQTT 客户端已断开")
