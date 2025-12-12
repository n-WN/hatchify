from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from hatchify.business.db.session import AsyncSessionLocal
from hatchify.business.models.execution import ExecutionTable
from hatchify.common.domain.enums.execution_status import ExecutionStatus
from hatchify.common.domain.event.base_event import StreamEvent, StartEvent, DoneEvent, ErrorEvent
from hatchify.core.stream_handler.event_listener.event_listener import EventListener


class ExecutionTrackerListener(EventListener):
    """
    执行状态跟踪监听器（基础设施层）

    监听 StreamEvent 并自动更新 ExecutionTable 状态

    事件映射：
    - StartEvent -> status = RUNNING, started_at = now
    - DoneEvent(completed) -> status = COMPLETED, completed_at = now
    - DoneEvent(cancel) -> status = CANCELLED, completed_at = now
    - DoneEvent(error) -> status = FAILED, completed_at = now
    - ErrorEvent -> 记录 error 字段
    """

    @property
    def name(self) -> str:
        return "ExecutionTrackerListener"

    async def on_event(self, execution_id: str, event: StreamEvent):
        """
        事件回调 - 根据事件类型更新执行状态

        Args:
            execution_id: 执行ID
            event: 流事件
        """
        try:
            match event.type:
                case "start":
                    await self._handle_start(execution_id, event.data)
                case "done":
                    await self._handle_done(execution_id, event.data)
                case "error":
                    await self._handle_error(execution_id, event.data)
                case _:
                    ...
        except Exception as e:
            logger.error(f"ExecutionTrackerListener failed for {execution_id}: {type(e).__name__}: {e}")

    async def _handle_start(self, execution_id: str, event_data: StartEvent):
        """处理 StartEvent: 更新为 RUNNING"""
        async with AsyncSessionLocal() as session:
            await self._update_execution(
                session,
                execution_id,
                status=ExecutionStatus.RUNNING,
                started_at=datetime.now()
            )

    async def _handle_done(self, execution_id: str, event_data: DoneEvent):
        """处理 DoneEvent: 根据 reason 更新为终态"""
        status_map = {
            "completed": ExecutionStatus.COMPLETED,
            "cancel": ExecutionStatus.CANCELLED,
            "error": ExecutionStatus.FAILED,
        }
        status = status_map.get(event_data.reason, ExecutionStatus.FAILED)

        async with AsyncSessionLocal() as session:
            await self._update_execution(
                session,
                execution_id,
                status=status,
                completed_at=datetime.now()
            )

    async def _handle_error(self, execution_id: str, event_data: ErrorEvent):
        """处理 ErrorEvent: 记录错误信息"""
        async with AsyncSessionLocal() as session:
            await self._update_execution(
                session,
                execution_id,
                error=event_data.reason
            )

    @staticmethod
    async def _update_execution(
            session: AsyncSession,
            execution_id: str,
            status: Optional[ExecutionStatus] = None,
            error: Optional[str] = None,
            started_at: Optional[datetime] = None,
            completed_at: Optional[datetime] = None,
    ):
        """更新执行记录"""
        result = await session.get(ExecutionTable, execution_id)
        if not result:
            logger.warning(f"Execution {execution_id} not found in database")
            return

        # 只更新提供的字段
        if status is not None:
            result.status = status
        if error is not None:
            result.error = error
        if started_at is not None:
            result.started_at = started_at
        if completed_at is not None:
            result.completed_at = completed_at

        await session.commit()
        logger.debug(f"Execution {execution_id} updated: status={status}")
