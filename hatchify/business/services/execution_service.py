from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from hatchify.business.manager.repository_manager import RepositoryManager
from hatchify.business.models.execution import ExecutionTable
from hatchify.business.repositories.execution_repository import ExecutionRepository
from hatchify.business.services.base.generic_service import GenericService
from hatchify.common.domain.enums.execution_status import ExecutionStatus
from hatchify.common.domain.enums.execution_type import ExecutionType


class ExecutionService(GenericService[ExecutionTable]):

    def __init__(self):
        super().__init__(ExecutionTable, ExecutionRepository)
        self._repository: ExecutionRepository = RepositoryManager.get_repository(ExecutionRepository)

    async def create_execution(
            self,
            session: AsyncSession,
            execution_type: ExecutionType,
            graph_id: Optional[str] = None,
            session_id: Optional[str] = None,
    ) -> ExecutionTable:
        """
        创建执行记录

        Args:
            session: 数据库会话
            execution_type: 执行类型
            graph_id: Graph ID（可选）
            session_id: 会话ID（可选）

        Returns:
            创建的执行记录
        """
        execution = ExecutionTable(
            type=execution_type,
            status=ExecutionStatus.PENDING,
            graph_id=graph_id,
            session_id=session_id,
        )
        await self._repository.save(session, execution)
        await session.commit()
        return execution

