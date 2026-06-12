"""
应用入口

初始化日志、加载配置、构建处理器注册表，并启动 MQTT 监听。
"""

import logging
import signal
import sys

from wechat_mqtt.config import load_config
from wechat_mqtt.handlers.registry import HandlerRegistry
from wechat_mqtt.logging_setup import setup_logging
from wechat_mqtt.mqtt_client import MqttListener


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)
    logger = logging.getLogger("main")

    logger.info("--- wechat-mqtt 启动中 ---")

    registry = HandlerRegistry(enabled_handlers=config.enabled_handlers)
    listener = MqttListener(config.mqtt, registry)

    def _signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭 ...")
        listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        listener.run_forever()
    except Exception as e:
        logger.critical(f"运行时发生严重错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
