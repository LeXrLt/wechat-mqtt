"""
调试日志处理器

将收到的微信消息以 DEBUG 级别输出到日志，用于调试和验证消息链路。
"""

from wechat_mqtt.handlers.base import BaseHandler
from wechat_mqtt.models import WechatMessage


class DebugHandler(BaseHandler):
    """
    调试处理器：将消息输出到 DEBUG 日志。

    输出格式：【消息来源：（私聊|群聊）】【发送人】【消息内容】
    """

    name = "debug"
    priority = 1000

    def handle(self, message: WechatMessage) -> None:
        room = f"{message.room_name} - " if message.is_group else ""
        self.logger.debug(
            f"【消息来源：{message.source_label}】"
            f"【{room}{message.speaker_name}】"
            f"【{message.content}】"
        )
