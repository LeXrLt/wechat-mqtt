"""
数据库连接与会话管理

使用 SQLAlchemy 2.0 提供 engine 与 session。
"""

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# 语义向量维度。修改此值需同步调整数据库迁移中的 Vector 维度。
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""

    pass


def build_database_url() -> str:
    """
    构建数据库连接 URL。

    优先使用 DATABASE_URL，否则由 POSTGRES_* 环境变量拼装。
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "wechat")
    password = os.getenv("POSTGRES_PASSWORD", "wechat")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "wechat")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


_engine = None
_SessionLocal = None


def get_engine():
    """获取全局 engine（懒加载单例）。"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            build_database_url(),
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """获取 session 工厂（懒加载单例）。"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    提供一个事务性的会话上下文。

    用法：
        with session_scope() as session:
            ...
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
