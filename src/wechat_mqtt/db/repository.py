"""
数据访问层 (Repository)

封装常用的数据库读写操作，供消息处理器及后续 skill 复用。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from wechat_mqtt.db.models import Chatroom, Contact, Message
from wechat_mqtt.models import WechatMessage


def get_or_create_contact(session: Session, name: str) -> Optional[Contact]:
    """根据名称获取或创建联系人。名称为空时返回 None。"""
    if not name:
        return None
    contact = session.scalar(select(Contact).where(Contact.name == name))
    if contact is None:
        contact = Contact(name=name)
        session.add(contact)
        session.flush()
    return contact


def get_or_create_chatroom(session: Session, name: str) -> Optional[Chatroom]:
    """根据名称获取或创建群聊。名称为空时返回 None。"""
    if not name:
        return None
    room = session.scalar(select(Chatroom).where(Chatroom.name == name))
    if room is None:
        room = Chatroom(name=name)
        session.add(room)
        session.flush()
    return room


def _parse_timestamp(message: WechatMessage) -> Optional[datetime]:
    """尽力将上游时间戳解析为 datetime。"""
    ts = message.timestamp
    if ts is None:
        return None
    try:
        # 数字时间戳（秒）
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        # ISO 字符串
        if isinstance(ts, str) and ts.isdigit():
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        if isinstance(ts, str):
            return datetime.fromisoformat(ts)
    except (ValueError, OSError, OverflowError):
        return None
    return None


def save_message(session: Session, message: WechatMessage) -> Message:
    """
    将一条微信消息持久化到数据库。

    会自动 get_or_create 关联的联系人与群聊。

    参数：
        session (Session): 数据库会话
        message (WechatMessage): 待保存的消息

    返回：
        Message: 已保存的 ORM 消息对象
    """
    sender = get_or_create_contact(session, message.speaker_name)
    chatroom = (
        get_or_create_chatroom(session, message.room_name)
        if message.is_group
        else None
    )

    db_message = Message(
        msg_type=message.msg_type,
        chatroom_id=chatroom.id if chatroom else None,
        sender_id=sender.id if sender else None,
        sender_name=message.speaker_name,
        room_name=message.room_name or None,
        is_group=message.is_group,
        is_bot=message.is_bot,
        content=message.content,
        msg_timestamp=_parse_timestamp(message),
        raw=message.raw,
    )
    session.add(db_message)
    session.flush()
    return db_message
