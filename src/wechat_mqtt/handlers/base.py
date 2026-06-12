"""
消息处理器基类

所有消息处理器都应继承自 BaseHandler，实现 handle 方法。
通过这种方式可以方便地扩展新的消息处理逻辑。
"""

import logging
from abc import ABC, abstractmethod

from wechat_mqtt.models import WechatMessage


class BaseHandler(ABC):
    """
    消息处理器抽象基类。

    属性：
        name (str): 处理器唯一名称，用于配置启用/禁用
        priority (int): 优先级，数值越大越先执行
    """

    name: str = "base"
    priority: int = 0

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"handler.{self.name}")

    @abstractmethod
    def handle(self, message: WechatMessage) -> None:
        """
        处理一条微信消息。

        参数：
            message (WechatMessage): 收到的消息对象

        返回：
            None
        """
        raise NotImplementedError
