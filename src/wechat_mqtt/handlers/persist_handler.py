"""
持久化处理器

将收到的微信消息存储到 PostgreSQL 数据库，供后续 agent skill 查询、
语义搜索与智能总结使用。
"""

from wechat_mqtt.db.database import session_scope
from wechat_mqtt.db.repository import save_message
from wechat_mqtt.handlers.base import BaseHandler
from wechat_mqtt.models import WechatMessage


class PersistHandler(BaseHandler):
    """将消息持久化到数据库的处理器。"""

    name = "persist"
    priority = 900

    def handle(self, message: WechatMessage) -> None:
        with session_scope() as session:
            db_message = save_message(session, message)
            self.logger.debug(f"消息已入库 id={db_message.id}")
