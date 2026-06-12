"""initial schema

创建聊天记录相关表、pg_trgm 与 pgvector 扩展，以及检索索引。

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

from wechat_mqtt.db.database import EMBEDDING_DIM

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 扩展：pg_trgm 用于中文/关键词模糊检索，vector 用于语义搜索
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # contacts
    op.create_table(
        "contacts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("wxid", sa.String(128), unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("remark", sa.String(256)),
        sa.Column("avatar", sa.String(512)),
        sa.Column("extra", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contacts_name", "contacts", ["name"])

    # chatrooms
    op.create_table(
        "chatrooms",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("room_wxid", sa.String(128), unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("extra", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chatrooms_name", "chatrooms", ["name"])

    # room_members
    op.create_table(
        "room_members",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("chatroom_id", sa.BigInteger(), sa.ForeignKey("chatrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(256)),
        sa.Column("role", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("chatroom_id", "contact_id", name="uq_room_member"),
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("msg_id", sa.String(128)),
        sa.Column("msg_type", sa.String(64), nullable=False, server_default=""),
        sa.Column("chatroom_id", sa.BigInteger(), sa.ForeignKey("chatrooms.id", ondelete="SET NULL")),
        sa.Column("sender_id", sa.BigInteger(), sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("sender_name", sa.String(256), server_default=""),
        sa.Column("room_name", sa.String(256)),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("msg_timestamp", sa.DateTime(timezone=True)),
        sa.Column("raw", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_msg_id", "messages", ["msg_id"])
    op.create_index("ix_messages_chatroom_id", "messages", ["chatroom_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_msg_timestamp", "messages", ["msg_timestamp"])
    op.create_index("ix_messages_room_time", "messages", ["chatroom_id", "msg_timestamp"])
    op.create_index("ix_messages_sender_time", "messages", ["sender_id", "msg_timestamp"])
    # 内容模糊/关键词检索（pg_trgm GIN）
    op.execute(
        "CREATE INDEX ix_messages_content_trgm ON messages USING gin (content gin_trgm_ops)"
    )

    # message_embeddings
    op.create_table(
        "message_embeddings",
        sa.Column("message_id", sa.BigInteger(), sa.ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("model", sa.String(128), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # 语义搜索向量索引（HNSW，余弦距离）
    op.execute(
        "CREATE INDEX ix_message_embeddings_vec ON message_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # conversation_summaries
    op.create_table(
        "conversation_summaries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("scope", sa.String(32), nullable=False, server_default="room"),
        sa.Column("chatroom_id", sa.BigInteger(), sa.ForeignKey("chatrooms.id", ondelete="SET NULL")),
        sa.Column("contact_id", sa.BigInteger(), sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("message_count", sa.Integer(), server_default="0"),
        sa.Column("summary", sa.Text(), server_default=""),
        sa.Column("keywords", JSONB()),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_summary_scope_time",
        "conversation_summaries",
        ["scope", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_table("conversation_summaries")
    op.execute("DROP INDEX IF EXISTS ix_message_embeddings_vec")
    op.drop_table("message_embeddings")
    op.execute("DROP INDEX IF EXISTS ix_messages_content_trgm")
    op.drop_table("messages")
    op.drop_table("room_members")
    op.drop_table("chatrooms")
    op.drop_table("contacts")
