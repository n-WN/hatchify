from typing import Any, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from hatchify.business.manager.repository_manager import RepositoryManager
from hatchify.business.manager.service_manager import ServiceManager
from hatchify.business.models.graph_version import GraphVersionTable
from hatchify.business.repositories.graph_version_repository import GraphVersionRepository
from hatchify.business.services.base.generic_service import GenericService
from hatchify.business.services.session_service import SessionService


class GraphVersionService(GenericService[GraphVersionTable]):

    def __init__(self):
        super().__init__(GraphVersionTable, GraphVersionRepository)
        self._session_service: SessionService = ServiceManager.get_service(SessionService)

    async def delete_by_id(
            self,
            session: AsyncSession,
            entity_id: Any,
            commit: bool = True
    ) -> bool:
        """
        删除 GraphVersion 时自动级联删除关联的 Session（及其 Message）
        """
        try:
            # 1. 获取 GraphVersion 记录
            version = await self._repository.find_by_id(session, entity_id)
            if not version:
                return False

            # 2. 如果有 branch_session_id，删除该 Session（会自动删除 Message）
            if version.branch_session_id:
                await self._session_service.delete_by_id(
                    session,
                    version.branch_session_id,
                    commit=False  # 不立即提交，等整体操作完成
                )

            # 3. 删除 GraphVersion 记录
            result = await self._repository.delete_by_id(session, entity_id)

            if result and commit:
                await session.commit()

            return result
        except Exception as e:
            if commit:
                await session.rollback()
            raise

    async def delete_by_ids(
            self,
            session: AsyncSession,
            entity_ids: Iterable[Any],
            commit: bool = True
    ) -> bool:
        """
        批量删除多个 GraphVersion 时自动级联删除关联的 Session（及其 Message）
        """
        try:
            ids = list(entity_ids)
            if not ids:
                return False

            # 1. 获取所有 GraphVersion 记录
            versions = []
            for version_id in ids:
                version = await self._repository.find_by_id(session, version_id)
                if version:
                    versions.append(version)

            if not versions:
                return False

            # 2. 收集所有需要删除的 branch_session_id
            session_ids_to_delete = [
                v.branch_session_id
                for v in versions
                if v.branch_session_id
            ]

            # 3. 批量删除 Session（会自动删除 Message）
            if session_ids_to_delete:
                await self._session_service.delete_by_ids(
                    session,
                    session_ids_to_delete,
                    commit=False  # 不立即提交
                )

            # 4. 批量删除 GraphVersion 记录
            result = await self._repository.delete_in(session, ids)

            if result and commit:
                await session.commit()

            return result
        except Exception as e:
            if commit:
                await session.rollback()
            raise
