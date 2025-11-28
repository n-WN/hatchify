import mimetypes
from typing import Optional, cast, Any, Dict, List, Union, get_args, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from strands.models.litellm import LiteLLMModel
from strands.types.content import ContentBlock, Role, Messages, Message
from strands.types.media import DocumentFormat, VideoFormat, ImageFormat, DocumentContent, ImageContent, VideoContent

from app.business.db.session import transaction
from app.business.manager.repository_manager import RepositoryManager
from app.business.models.graph import GraphTable
from app.business.models.graph_version import GraphVersionTable
from app.business.models.messages import MessageTable
from app.business.models.session import SessionTable
from app.business.repositories.graph_repository import GraphRepository
from app.business.repositories.graph_version_repository import GraphVersionRepository
from app.business.repositories.message_repository import MessageRepository
from app.business.repositories.session_repository import SessionRepository
from app.business.services.base.generic_service import GenericService
from app.common.domain.entity.graph_spec import GraphSpec
from app.common.domain.enums.conversation_mode import ConversationMode
from app.common.domain.enums.graph_version_type import GraphVersionType
from app.common.domain.enums.message_role import MessageRole
from app.common.domain.enums.session_scene import SessionScene
from app.common.domain.requests.graph import ConversationRequest
from app.core.graph.graph_spec_generator import GraphSpecGenerator
from app.core.manager.function_manager import function_router
from app.core.manager.model_card_manager import model_card_manager
from app.core.manager.tool_manager import tool_factory

document_formats = get_args(DocumentFormat)
image_formats = get_args(ImageFormat)
video_formats = get_args(VideoFormat)


class GraphService(GenericService[GraphTable]):

    def __init__(self):
        super().__init__(GraphTable, GraphRepository)
        # 显式标注 repository 类型，让 IDE 知道可以调用 GraphRepository 的方法
        self._repository: GraphRepository = RepositoryManager.get_repository(GraphRepository)
        self._version_repo: GraphVersionRepository = RepositoryManager.get_repository(GraphVersionRepository)
        self._session_repo: SessionRepository = RepositoryManager.get_repository(SessionRepository)
        self._message_repo: MessageRepository = RepositoryManager.get_repository(MessageRepository)

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

    @staticmethod
    def _normalize_role(role: Union[str | Role | MessageRole]) -> MessageRole:
        if isinstance(role, MessageRole):
            return role
        else:
            match role:
                case MessageRole.ASSISTANT.value:
                    return MessageRole.ASSISTANT
                # case MessageRole.SYSTEM.value:
                #     return MessageRole.SYSTEM
                # case MessageRole.TOOL.value:
                #     return MessageRole.TOOL
                case MessageRole.USER.value | _:
                    return MessageRole.USER

    @staticmethod
    async def clean_strands_messages(messages: Messages):
        for message in messages:
            contents: List[ContentBlock] = message.get("content", [])
            for content in contents:

                video_content: VideoContent = content.get("video")
                if document_content := cast(DocumentContent, content.get("document")):
                    content_type = mimetypes.guess_type(cast(str, document_content.get("format")))
                if image_content := cast(ImageContent, content.get("image")):
                    content_type = mimetypes.guess_type(cast(str, image_content.get("format")))
                if video_content := cast(VideoContent, content.get("video")):
                    content_type = mimetypes.guess_type(cast(str, video_content.get("format")))

    async def _get_recent_messages(
            self,
            session: AsyncSession,
            session_id: str,
            limit: int = 10,
    ) -> Sequence[MessageTable]:
        """
        按条数拉取指定 session 的历史消息（默认最近 20 条），按 created_at 升序。
        """
        limit = max(limit, 1)
        return await self._message_repo.find_by(
            session,
            session_id=session_id,
            limit=limit,
            sort="created_at:asc",
        )

    @staticmethod
    def _db_messages_to_messages(db_messages: Sequence[MessageTable]) -> Messages:
        messages: Messages = []
        for msg in db_messages:
            messages.append(Message(
                role=msg.role.value,  # type: ignore
                content=cast(List[ContentBlock], msg.content)
            ))
        return messages

    async def get_graph_spec(
            self,
            session: AsyncSession,
            graph_id: str
    ) -> GraphSpec | None:
        graph_obj = await self.get_by_id(session, graph_id)
        if not graph_obj or not graph_obj.current_spec:
            return None
        return GraphSpec.model_validate(graph_obj.current_spec)

    async def conversation(
            self,
            session: AsyncSession,
            session_id: str,
            request: ConversationRequest,
    ) -> Dict[str, Any]:
        # TODO 目前仅支持用户文本，暂不支持其他消息类型和二进制内容
        history_db_messages = await self._get_recent_messages(session, session_id)
        history_messages: List[Dict[str, Any]] = LiteLLMModel.format_request_messages(self._db_messages_to_messages(history_db_messages))
        user_messages = LiteLLMModel.format_request_messages(request.messages)

        async with transaction(session):
            graph_obj: GraphTable | None = None
            session_obj = await self._session_repo.find_by_id(session, session_id)
            generator = GraphSpecGenerator(
                model_card_manager=model_card_manager,
                tool_router=tool_factory,
                function_router=function_router,
            )

            # create session and graph table
            if not session_obj:
                graph_obj = await self.create(
                    session,
                    {
                        "name": f"graph_{session_id}",
                        "description": "Auto generated from conversation",
                        "current_spec": {},
                    },
                    commit=False,
                )
                session_obj = SessionTable(
                    id=session_id,
                    graph_id=cast(str, graph_obj.id),
                    scene=SessionScene.GRAPH_EDIT,
                )
                await self._session_repo.save(session, session_obj)
            else:
                graph_obj = await self.get_by_id(session, cast(str, session_obj.graph_id))
                if not graph_obj:
                    graph_obj = await self.create(
                        session,
                        {
                            "name": f"graph_{session_obj.graph_id}_recreated",
                            "description": "Recreated for missing graph",
                            "current_spec": {},
                        },
                        commit=False,
                    )
                    await self._session_repo.update_by_id(
                        session,
                        cast(str, session_obj.id),
                        {"graph_id": cast(str, graph_obj.id)},
                    )

            graph_spec = await generator.generate_graph_spec(
                pre_graph_spec=cast(Dict[str, Any], graph_obj.current_spec),
                user_messages=user_messages,
                history_messages=history_messages
            )

            assistant_reply = graph_spec.model_dump_json(indent=2, ensure_ascii=False)

            if request.mode == ConversationMode.EDIT:
                update_data: Dict[str, Any] = {
                    "spec": graph_spec.model_dump(),
                    "name": graph_spec.name,
                    "description": graph_spec.description,
                }
                updated = await self.update_by_id(
                    session,
                    cast(str, graph_obj.id),
                    update_data,
                    commit=False,
                )
                graph_obj = updated or graph_obj

            # write record
            for msg in request.messages:
                role: Role = msg.get("role")
                normalize_role = self._normalize_role(role)
                content: List[ContentBlock] = msg.get("content")
                await self._message_repo.save(
                    session,
                    MessageTable(
                        session_id=cast(str, session_obj.id),
                        role=normalize_role,
                        content=content
                    ),
                )
            await self._message_repo.save(
                session,
                MessageTable(
                    session_id=cast(str, session_obj.id),
                    role=MessageRole.ASSISTANT,
                    content=[ContentBlock(text=assistant_reply)],
                ),
            )

            await session.flush()

        return {
            "graph_id": cast(str, graph_obj.id),
            "spec": graph_spec.model_dump()
        }

    async def create_snapshot(
            self,
            session: AsyncSession,
            graph_id: str,
            session_id: Optional[str] = None,
            message_id: Optional[str] = None,
            comment: Optional[str] = None,
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
                "type": GraphVersionType.SNAPSHOT,
                "version": new_version,
                "spec": graph.current_spec,
                "session_id": session_id,
                "message_id": message_id,
                "comment": comment,
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

    async def _create_draft_snapshot(
            self,
            session: AsyncSession,
            graph: GraphTable,
            comment: Optional[str] = None,
            session_id: Optional[str] = None,
            message_id: Optional[str] = None,
    ) -> GraphVersionTable:
        """
        为 Graph 创建草稿快照（最多保留 3 条，超出则删除最早的）
        """
        drafts = await self._version_repo.list_drafts_by_graph(session, graph.id)
        while len(drafts) >= 3:
            oldest = drafts.pop(0)
            await self._version_repo.delete_by_id(session, oldest.id)

        draft = GraphVersionTable(
            graph_id=graph.id,
            type=GraphVersionType.DRAFT,
            version=None,
            spec=graph.current_spec,
            comment=comment or "auto-draft",
            session_id=session_id,
            message_id=message_id,
        )
        await self._version_repo.save(session, draft)
        await session.flush()
        return draft

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
            graph = await self._repository.get_by_id_with_lock(session, graph_id)
            if not graph:
                raise ValueError(f"Graph {graph_id} not found")

            # 1. 获取指定版本
            target_version = await self._version_repo.find_by_id(session, version_id)
            if not target_version:
                raise ValueError(f"GraphVersion {version_id} not found")

            if target_version.graph_id != graph_id:
                raise ValueError(
                    f"GraphVersion {version_id} does not belong to Graph {graph_id}"
                )

            if target_version.type != GraphVersionType.SNAPSHOT:
                raise ValueError("Only SNAPSHOT versions can be used for rollback")

            # 2. 检测当前工作区是否 dirty
            dirty = graph.current_version_id is None
            if not dirty and graph.current_version_id is not None:
                current_version = await self._version_repo.find_by_id(
                    session, graph.current_version_id
                )
                if (not current_version) or graph.current_spec != current_version.spec:
                    dirty = True

            # 3. 如果 dirty，先创建草稿快照
            if dirty:
                await self._create_draft_snapshot(
                    session=session,
                    graph=graph,
                    comment="auto-draft before rollback",
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
