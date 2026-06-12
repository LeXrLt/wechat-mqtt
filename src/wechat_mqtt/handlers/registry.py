"""
处理器注册与分发

负责收集所有 BaseHandler 子类、根据配置过滤启用项，并按优先级依次分发消息。
新增处理器只需在 handlers 包中实现 BaseHandler 子类并在此处导入即可。
"""

import logging
from typing import List, Type

from wechat_mqtt.handlers.base import BaseHandler
from wechat_mqtt.handlers.debug_handler import DebugHandler
from wechat_mqtt.handlers.persist_handler import PersistHandler
from wechat_mqtt.models import WechatMessage

logger = logging.getLogger(__name__)

# 所有可用的处理器类，新增处理器在此注册（按优先级降序执行）
ALL_HANDLERS: List[Type[BaseHandler]] = [
    DebugHandler,
    PersistHandler,
]


class HandlerRegistry:
    """
    处理器注册表，负责实例化、过滤并按优先级分发消息。
    """

    def __init__(self, enabled_handlers: List[str] = None) -> None:
        self.enabled_handlers = enabled_handlers or []
        self.handlers: List[BaseHandler] = self._build_handlers()

    def _build_handlers(self) -> List[BaseHandler]:
        """根据配置构建启用的处理器实例列表。"""
        selected: List[BaseHandler] = []
        for handler_cls in ALL_HANDLERS:
            if self.enabled_handlers and handler_cls.name not in self.enabled_handlers:
                continue
            selected.append(handler_cls())

        # 按优先级降序排序
        selected.sort(key=lambda h: h.priority, reverse=True)
        names = ", ".join(h.name for h in selected) or "(无)"
        logger.info(f"已加载处理器: {names}")
        return selected

    def dispatch(self, message: WechatMessage) -> None:
        """
        将消息依次分发给所有启用的处理器。

        参数：
            message (WechatMessage): 收到的消息对象
        """
        for handler in self.handlers:
            try:
                handler.handle(message)
            except Exception as e:
                logger.error(
                    f"处理器 '{handler.name}' 处理消息时发生错误: {e}", exc_info=True
                )
