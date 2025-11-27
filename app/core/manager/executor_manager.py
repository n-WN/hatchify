"""
GraphExecutor 管理器

用于管理多个 GraphExecutor 实例，支持：
- 创建和注册 executor
- 通过 graph_id 获取 executor
- 清理完成的 executor
"""
import asyncio
from typing import Dict, Optional

from loguru import logger

from app.core.graph.graph_executor import GraphExecutor


class ExecutorManager:
    """
    全局 Executor 管理器（单例模式）

    管理所有活跃的 GraphExecutor 实例
    """

    # 类级别存储
    _executors: Dict[str, GraphExecutor] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def create(
        cls,
        graph_id: str,
        executor: GraphExecutor
    ) -> GraphExecutor:
        """
        创建并注册 executor

        Args:
            graph_id: 图执行唯一 ID
            executor: GraphExecutor 实例

        Returns:
            注册的 executor

        Raises:
            ValueError: 如果 graph_id 已存在
        """
        async with cls._lock:
            if graph_id in cls._executors:
                raise ValueError(f"Executor with graph_id '{graph_id}' already exists")

            cls._executors[graph_id] = executor
            logger.info(f"Created executor for graph: {graph_id}")
            return executor

    @classmethod
    async def get(cls, graph_id: str) -> Optional[GraphExecutor]:
        """
        获取 executor

        Args:
            graph_id: 图执行唯一 ID

        Returns:
            GraphExecutor 实例，如果不存在返回 None
        """
        async with cls._lock:
            return cls._executors.get(graph_id)

    @classmethod
    async def get_or_raise(cls, graph_id: str) -> GraphExecutor:
        """
        获取 executor，不存在则抛出异常

        Args:
            graph_id: 图执行唯一 ID

        Returns:
            GraphExecutor 实例

        Raises:
            ValueError: 如果 executor 不存在
        """
        executor = await cls.get(graph_id)
        if not executor:
            raise ValueError(f"Executor with graph_id '{graph_id}' not found")
        return executor

    @classmethod
    async def delete(cls, graph_id: str) -> bool:
        """
        删除 executor

        Args:
            graph_id: 图执行唯一 ID

        Returns:
            是否删除成功
        """
        async with cls._lock:
            if graph_id in cls._executors:
                del cls._executors[graph_id]
                logger.info(f"Deleted executor for graph: {graph_id}")
                return True
            return False

    @classmethod
    async def exists(cls, graph_id: str) -> bool:
        """
        检查 executor 是否存在

        Args:
            graph_id: 图执行唯一 ID

        Returns:
            是否存在
        """
        async with cls._lock:
            return graph_id in cls._executors

    @classmethod
    async def get_all_graph_ids(cls) -> list[str]:
        """获取所有活跃的 graph_id"""
        async with cls._lock:
            return list(cls._executors.keys())

    @classmethod
    async def count(cls) -> int:
        """获取活跃的 executor 数量"""
        async with cls._lock:
            return len(cls._executors)

    @classmethod
    async def clear(cls):
        """清空所有 executor（谨慎使用）"""
        async with cls._lock:
            count = len(cls._executors)
            cls._executors.clear()
            logger.warning(f"Cleared all {count} executors")