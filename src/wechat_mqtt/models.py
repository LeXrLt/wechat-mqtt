"""
消息数据模型

定义从 wechat-listener 通过 MQTT 接收到的消息结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class WechatMessage:
    """
    微信消息数据模型。

    对应 wechat-listener 的 push-msg-to-mqtt-plugin 推送的 JSON 结构。

    属性：
        room_name (str): 群名称，私聊时为空
        speaker_name (str): 发送人名称
        content (str): 消息内容
        is_bot (bool): 是否为机器人（自己）发送
        msg_type (str): 消息类型，如 Text/Quote
        timestamp (Optional[Any]): 原始时间戳
        time_str (Optional[str]): 格式化时间字符串
        raw (Dict[str, Any]): 原始 payload，保留全部字段以便扩展
    """

    room_name: str = ""
    speaker_name: str = ""
    content: str = ""
    is_bot: bool = False
    msg_type: str = ""
    timestamp: Optional[Any] = None
    time_str: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_group(self) -> bool:
        """是否为群聊消息。"""
        return bool(self.room_name)

    @property
    def source_label(self) -> str:
        """消息来源标签：群聊 或 私聊。"""
        return "群聊" if self.is_group else "私聊"

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "WechatMessage":
        """
        从 MQTT JSON payload 构建消息对象。

        参数：
            payload (Dict[str, Any]): 解析后的 JSON 字典

        返回：
            WechatMessage: 消息对象
        """
        return cls(
            room_name=payload.get("room_name", "") or "",
            speaker_name=payload.get("speaker_name", "") or "",
            content=payload.get("content", "") or "",
            is_bot=bool(payload.get("is_bot", False)),
            msg_type=str(payload.get("msg_type", "")),
            timestamp=payload.get("timestamp"),
            time_str=payload.get("time_str"),
            raw=payload,
        )
