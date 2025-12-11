from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from hatchify.business.db.session import AsyncSessionLocal
from hatchify.business.models.execution import ExecutionTable
from hatchify.common.domain.event.base_event import StreamEvent, ResultEvent
from hatchify.core.stream_handler.event_listener.event_listener import EventListener


class GraphMetadataListener(EventListener):
    """
    Graph 元数据监听器（业务层）

    监听 GraphSpecGenerator 发出的 result 事件，
    提取 graph_id 并更新 ExecutionTable

    适用场景：
    - GraphSpecGenerator 创建 Graph 后，更新 ExecutionTable 的 graph_id
    """

    @property
    def name(self) -> str:
        return "GraphMetadataListener"

    async def on_event(self, execution_id: str, event: StreamEvent):
        """
        监听 result 事件并更新 graph_id

        Args:
            execution_id: 执行ID
            event: 流事件
        """
        try:
            # 只关心 result 事件
            if event.type == "result":
                await self._handle_result(execution_id, event.data)
        except Exception as e:
            # 监听器失败不应影响主流程
            logger.error(f"GraphMetadataListener failed for {execution_id}: {type(e).__name__}: {e}")

    async def _handle_result(self, execution_id: str, event_data: ResultEvent):
        """
        处理 ResultEvent: 提取 graph_id 并更新

        Args:
            execution_id: 执行ID
            event_data: ResultEvent 数据
        """
        data = event_data.data

        # 检查是否包含 graph_id
        if isinstance(data, dict) and "graph_id" in data:
            graph_id = data["graph_id"]
            await self._update_graph_id(execution_id, graph_id)

    @staticmethod
    async def _update_graph_id(execution_id: str, graph_id: str):
        """
        更新 ExecutionTable 的 graph_id

        Args:
            execution_id: 执行ID
            graph_id: Graph ID
        """
        async with AsyncSessionLocal() as session:
            execution = await session.get(ExecutionTable, execution_id)
            if not execution:
                logger.warning(f"Execution {execution_id} not found in database")
                return

            execution.graph_id = graph_id
            await session.commit()
            logger.debug(f"Execution {execution_id} updated: graph_id={graph_id}")