"""消息处理器包。"""

from wechat_mqtt.handlers.base import BaseHandler
from wechat_mqtt.handlers.registry import HandlerRegistry

__all__ = ["BaseHandler", "HandlerRegistry"]
