from typing import Optional, Tuple, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.manager.repository_manager import RepositoryManager
from app.business.models.graph import GraphTable
from app.business.models.graph_version import GraphVersionTable
from app.business.repositories.graph_repository import GraphRepository
from app.business.repositories.graph_version_repository import GraphVersionRepository
from app.business.services.base.generic_service import GenericService


class GraphService(GenericService[GraphTable]):

    def __init__(self):
        super().__init__(GraphTable, GraphRepository)
        # 显式标注 repository 类型，让 IDE 知道可以调用 GraphRepository 的方法
        self._repository: GraphRepository = RepositoryManager.get_repository(GraphRepository)
        self._version_repo: GraphVersionRepository = RepositoryManager.get_repository(GraphVersionRepository)

    async def update_by_id(
        self,
        session: AsyncSession,
        entity_id: str,
        update_data: dict,
        commit: bool = True
    ) -> Optional[GraphTable]:
        """
        更新 Graph
        - 如果更新了 spec，current_version_id 会设为 NULL（标记有未保存修改）
        - 如果只更新 name/description，current_version_id 不变
        """
        try:
            # 如果更新了 spec，则标记为有未保存修改
            if "spec" in update_data:
                update_data["current_spec"] = update_data.pop("spec")
                update_data["current_version_id"] = None

            result = await self._repository.update_by_id(session, entity_id, update_data)

            if commit:
                await session.commit()
                if result:
                    await session.refresh(result)

            return result
        except Exception as e:
            if commit:
                await session.rollback()
            raise

    async def create_snapshot(
        self,
        session: AsyncSession,
        graph_id: str,
        session_id: Optional[str] = None,
        message_id: Optional[str] = None,
        commit: bool = True
    ) -> GraphVersionTable:
        """
        为 Graph 创建快照版本
        1. 读取 Graph.current_spec（加锁）
        2. 计算新的 version 号（max(version) + 1）
        3. 创建 GraphVersion
        4. 更新 Graph.current_version_id

        使用悲观锁防止并发创建相同版本号
        """
        try:
            # 1. 获取 Graph（加悲观锁）
            graph = await self._repository.get_by_id_with_lock(session, graph_id)
            if not graph:
                raise ValueError(f"Graph {graph_id} not found")

            # 2. 计算新的 version 号
            max_version = await self._version_repo.get_max_version_by_graph(
                session, graph_id
            )
            new_version = (max_version or 0) + 1

            # 3. 创建 GraphVersion
            version_data = {
                "graph_id": graph_id,
                "version": new_version,
                "spec": graph.current_spec,
                "session_id": session_id,
                "message_id": message_id,
            }
            new_graph_version = GraphVersionTable(**version_data)
            await self._version_repo.save(session, new_graph_version)
            await session.flush()

            # 4. 更新 Graph.current_version_id
            await self._repository.update_by_id(
                session,
                graph_id,
                {"current_version_id": new_graph_version.id}
            )

            if commit:
                await session.commit()
                await session.refresh(new_graph_version)

            return new_graph_version
        except Exception as e:
            if commit:
                await session.rollback()
            raise

    async def rollback_to_version(
        self,
        session: AsyncSession,
        graph_id: str,
        version_id: int,
        commit: bool = True
    ) -> GraphTable:
        """
        回滚到指定版本
        1. 读取指定 version 的 spec
        2. 更新 Graph.current_spec = 该版本的 spec
        3. 更新 Graph.current_version_id = version_id
        """
        try:
            # 1. 获取指定版本
            target_version = await self._version_repo.find_by_id(session, version_id)
            if not target_version:
                raise ValueError(f"GraphVersion {version_id} not found")

            if target_version.graph_id != graph_id:
                raise ValueError(
                    f"GraphVersion {version_id} does not belong to Graph {graph_id}"
                )

            # 2. 更新 Graph
            update_data = {
                "current_spec": target_version.spec,
                "current_version_id": version_id,
            }
            result = await self._repository.update_by_id(session, graph_id, update_data)

            if not result:
                raise ValueError(f"Failed to rollback Graph {graph_id}")

            if commit:
                await session.commit()
                await session.refresh(result)

            return result
        except Exception as e:
            if commit:
                await session.rollback()
            raise
