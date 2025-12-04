"""
事件存储模块，用于支持 SSE 断线重连
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger

from hatchify.common.domain.event.base_event import StreamEvent


class EventStore:
    _stores: Dict[str, 'EventStore'] = {}
    _lock = asyncio.Lock()

    def __init__(self, source_id: str, ttl_seconds: int = 900):
        """
        初始化事件存储

        Args:
            source_id: 图执行 ID
            ttl_seconds: 过期时间（秒），900秒
        """
        self.source_id = source_id
        self.events: List[StreamEvent] = []
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds
        self._completed = False

    @classmethod
    async def get_or_create(cls, source_id: str, ttl_seconds: int = 900) -> 'EventStore':
        """
        获取或创建事件存储（线程安全）

        Args:
            source_id: 图执行 ID
            ttl_seconds: 过期时间（秒）

        Returns:
            EventStore 实例
        """
        async with cls._lock:
            if source_id not in cls._stores:
                logger.debug(f"Creating new EventStore for graph: {source_id}")
                cls._stores[source_id] = EventStore(source_id, ttl_seconds)
            return cls._stores[source_id]

    @classmethod
    async def get(cls, source_id: str) -> Optional['EventStore']:
        """
        获取事件存储

        Args:
            source_id: 图执行 ID

        Returns:
            EventStore 实例，如果不存在返回 None
        """
        async with cls._lock:
            return cls._stores.get(source_id)

    @classmethod
    async def delete(cls, source_id: str) -> bool:
        """
        删除事件存储

        Args:
            source_id: 图执行 ID

        Returns:
            是否删除成功
        """
        async with cls._lock:
            if source_id in cls._stores:
                del cls._stores[source_id]
                logger.info(f"Deleted EventStore for graph: {source_id}")
                return True
            return False

    @classmethod
    async def cleanup_expired(cls):
        """
        清理过期的事件存储

        建议在定时任务中调用
        """
        async with cls._lock:
            now = datetime.now()
            expired = []

            for gid, store in cls._stores.items():
                age = now - store.created_at
                if age > timedelta(seconds=store.ttl_seconds):
                    expired.append(gid)

            for gid in expired:
                del cls._stores[gid]

            if expired:
                logger.info(f"Cleaned up {len(expired)} expired EventStores: {expired}")

    @classmethod
    async def get_all_source_ids(cls) -> List[str]:
        """获取所有活跃的 source_id"""
        async with cls._lock:
            return list(cls._stores.keys())

    def append(self, event: StreamEvent) -> None:
        """
        追加事件到存储

        Args:
            event: 图事件
        """
        self.events.append(event)

        # 检查是否完成
        if event.type == "done":
            self._completed = True
            logger.debug(f"EventStore marked as completed for graph: {self.source_id}")

    def get_after(self, last_event_id: Optional[str]) -> List[StreamEvent]:
        """
        获取指定事件 ID 之后的所有事件

        Args:
            last_event_id: 上次收到的事件 ID（客户端提供）

        Returns:
            事件列表
        """
        if not last_event_id:
            # 没有提供 ID，返回所有事件
            logger.debug(f"Returning all {len(self.events)} events (no last_event_id)")
            return self.events.copy()

        # 查找事件位置
        for i, event in enumerate(self.events):
            if event.id == last_event_id:
                # 返回该事件之后的所有事件
                remaining = self.events[i + 1:]
                logger.debug(f"Found last_event_id at index {i}, returning {len(remaining)} events")
                return remaining

        # ID 未找到，可能是太旧或无效，返回所有事件
        logger.warning(f"last_event_id '{last_event_id}' not found, returning all {len(self.events)} events")
        return self.events.copy()

    def get_all(self) -> List[StreamEvent]:
        """获取所有事件"""
        return self.events.copy()

    def is_completed(self) -> bool:
        """检查流是否已完成"""
        return self._completed

    def count(self) -> int:
        """获取事件数量"""
        return len(self.events)

    def get_first_event_id(self) -> Optional[str]:
        """获取第一个事件的 ID"""
        return self.events[0].id if self.events else None

    def get_last_event_id(self) -> Optional[str]:
        """获取最后一个事件的 ID"""
        return self.events[-1].id if self.events else None

    def clear(self) -> None:
        """清空所有事件"""
        self.events.clear()
        self._completed = False
        logger.debug(f"Cleared EventStore for graph: {self.source_id}")

    def __repr__(self) -> str:
        return (
            f"EventStore(source_id={self.source_id}, "
            f"events={len(self.events)}, "
            f"completed={self._completed}, "
            f"age={datetime.now() - self.created_at})"
        )
