from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hatchify.business.models.graph import GraphTable
from hatchify.business.repositories.base.generic_repository import GenericRepository


class GraphRepository(GenericRepository[GraphTable]):

    def __init__(self):
        super().__init__(GraphTable)

    async def get_by_id_with_lock(
            self,
            session: AsyncSession,
            graph_id: str
    ) -> Optional[GraphTable]:
        """
        获取 Graph 并加悲观锁（SELECT FOR UPDATE）
        用于版本创建等需要串行化的操作
        """
        stmt = (
            select(self.entity_type)
            .where(self.entity_type.id == graph_id)  # type: ignore
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
