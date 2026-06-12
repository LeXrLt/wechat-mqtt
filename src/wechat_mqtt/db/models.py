"""
ORM 数据模型

参照社交聊天应用的表设计，并兼顾 agent skill 的高效查询、语义搜索与智能总结需求。

表结构概览：
- contacts              联系人（微信用户）
- chatrooms             群聊
- room_members          群成员关系
- messages              消息主表
- message_embeddings    消息语义向量（用于语义搜索）
- conversation_summaries 会话智能总结
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wechat_mqtt.db.database import EMBEDDING_DIM, Base


class TimestampMixin:
    """通用创建/更新时间戳。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Contact(TimestampMixin, Base):
    """联系人（微信用户）。"""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    wxid: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    remark: Mapped[Optional[str]] = mapped_column(String(256))
    avatar: Mapped[Optional[str]] = mapped_column(String(512))
    extra: Mapped[Optional[dict]] = mapped_column(JSONB)

    messages: Mapped[List["Message"]] = relationship(back_populates="sender")


class Chatroom(TimestampMixin, Base):
    """群聊。"""

    __tablename__ = "chatrooms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    room_wxid: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("contacts.id", ondelete="SET NULL")
    )
    extra: Mapped[Optional[dict]] = mapped_column(JSONB)

    messages: Mapped[List["Message"]] = relationship(back_populates="chatroom")
    members: Mapped[List["RoomMember"]] = relationship(back_populates="chatroom")


class RoomMember(TimestampMixin, Base):
    """群成员关系。"""

    __tablename__ = "room_members"
    __table_args__ = (
        UniqueConstraint("chatroom_id", "contact_id", name="uq_room_member"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chatroom_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chatrooms.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(256))
    role: Mapped[Optional[str]] = mapped_column(String(32))

    chatroom: Mapped["Chatroom"] = relationship(back_populates="members")
    contact: Mapped["Contact"] = relationship()


class Message(Base):
    """消息主表。"""

    __tablename__ = "messages"
    __table_args__ = (
        # 按会话 + 时间倒序查询（最常用的检索路径）
        Index("ix_messages_room_time", "chatroom_id", "msg_timestamp"),
        Index("ix_messages_sender_time", "sender_id", "msg_timestamp"),
        # 基于 pg_trgm 的内容模糊/关键词检索（迁移中创建 GIN 索引）
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 源消息 ID，用于去重（如果上游提供）
    msg_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    msg_type: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    chatroom_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chatrooms.id", ondelete="SET NULL"), index=True
    )
    sender_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("contacts.id", ondelete="SET NULL"), index=True
    )
    # 冗余存储名称，便于无需 join 的快速展示
    sender_name: Mapped[str] = mapped_column(String(256), default="")
    room_name: Mapped[Optional[str]] = mapped_column(String(256))

    is_group: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    content: Mapped[str] = mapped_column(Text, default="")
    # 消息发生时间（来自上游），与入库时间 created_at 区分
    msg_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), index=True
    )
    # 完整原始 payload，便于后续扩展解析
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sender: Mapped[Optional["Contact"]] = relationship(back_populates="messages")
    chatroom: Mapped[Optional["Chatroom"]] = relationship(back_populates="messages")
    embedding: Mapped[Optional["MessageEmbedding"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", uselist=False
    )


class MessageEmbedding(Base):
    """消息语义向量，用于语义/相似度搜索。"""

    __tablename__ = "message_embeddings"

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    embedding: Mapped[list] = mapped_column(Vector(EMBEDDING_DIM))
    model: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    message: Mapped["Message"] = relationship(back_populates="embedding")


class ConversationSummary(Base):
    """
    会话智能总结。

    支持按群聊、联系人或全局维度，对某段时间内的消息生成总结，
    并可存储总结向量以支持对总结的语义检索。
    """

    __tablename__ = "conversation_summaries"
    __table_args__ = (
        Index("ix_summary_scope_time", "scope", "period_start", "period_end"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 总结范围：room（群聊）/ contact（私聊）/ global（全局）
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="room")
    chatroom_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chatrooms.id", ondelete="SET NULL")
    )
    contact_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("contacts.id", ondelete="SET NULL")
    )
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[Optional[dict]] = mapped_column(JSONB)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
