from typing import Any, Iterable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from hatchify.business.manager.repository_manager import RepositoryManager
from hatchify.business.models.messages import MessageTable
from hatchify.business.models.session import SessionTable
from hatchify.business.repositories.message_repository import MessageRepository
from hatchify.business.repositories.session_repository import SessionRepository
from hatchify.business.services.base.generic_service import GenericService


class SessionService(GenericService[SessionTable]):

    def __init__(self):
        super().__init__(SessionTable, SessionRepository)
        self._message_repo: MessageRepository = RepositoryManager.get_repository(MessageRepository)

    async def delete_by_id(
            self,
            session: AsyncSession,
            entity_id: Any,
            commit: bool = True
    ) -> bool:
        """
        删除 Session 时自动级联删除所有 Message
        """
        try:
            # 1. 批量删除该 Session 下的所有 Message
            messages = await self._message_repo.find_by(
                session,
                session_id=entity_id,
            )
            if messages:
                message_ids = [msg.id for msg in messages]
                await self._message_repo.delete_in(session, message_ids)

            # 2. 删除 Session 记录
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
        批量删除多个 Session 时自动级联删除所有关联的 Message
        """
        try:
            ids = list(entity_ids)
            if not ids:
                return False

            # 1. 批量删除所有 Session 下的所有 Message
            all_message_ids = []
            for session_id in ids:
                messages = await self._message_repo.find_by(
                    session,
                    session_id=session_id,
                )
                if messages:
                    all_message_ids.extend([msg.id for msg in messages])

            if all_message_ids:
                await self._message_repo.delete_in(session, all_message_ids)

            # 2. 批量删除 Session 记录
            result = await self._repository.delete_in(session, ids)

            if result and commit:
                await session.commit()

            return result
        except Exception as e:
            if commit:
                await session.rollback()
            raise

    async def fork_session_with_messages(
            self,
            session: AsyncSession,
            new_session_data: dict,
            messages_to_copy: List[MessageTable],
            commit: bool = True
    ) -> SessionTable:
        """
        创建分支会话并批量复制消息

        用于版本快照和草稿创建时，复制完整的对话历史到新的会话分支

        Args:
            session: 数据库会话
            new_session_data: 新 Session 的数据（graph_id, parent_session_id, fork_from_message_id 等）
            messages_to_copy: 需要复制的消息列表
            commit: 是否立即提交事务

        Returns:
            创建的新 Session 对象
        """
        try:
            # 1. 创建新 Session
            new_session = await self.create(session, new_session_data, commit=False)

            # 2. 批量复制 Message
            if messages_to_copy:
                clones = [
                    MessageTable(
                        session_id=new_session.id,
                        role=msg.role,
                        content=msg.content,
                        token_usage=msg.token_usage,
                        meta_data=msg.meta_data,
                    )
                    for msg in messages_to_copy
                ]
                await self._message_repo.save_all(session, clones)
                await session.flush()

            if commit:
                await session.commit()
                await session.refresh(new_session)

            return new_session
        except Exception as e:
            if commit:
                await session.rollback()
            raise
