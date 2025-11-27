from typing import Optional, List, Dict

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.manager.repository_manager import RepositoryManager
from app.business.models.graph import GraphTable
from app.business.repositories.agent_repository import AgentRepository
from app.business.repositories.graph_repository import GraphRepository
from app.business.services.base.generic_service import GenericService
from app.business.utils.pagination_utils import CustomParams
from app.common.domain.responses.agent_response import AgentResponse
from app.common.domain.responses.graph_response import GraphResponse
from app.common.domain.responses.pagination import PaginationInfo


class GraphService(GenericService[GraphTable]):

    def __init__(self):
        super().__init__(GraphTable, GraphRepository)
        self._agent_repository: AgentRepository = RepositoryManager.get_repository(AgentRepository)

    async def _build_graph_response(
            self,
            session: AsyncSession,
            graph: GraphTable,
    ) -> GraphResponse:

        agents = await self._agent_repository.find_by(
            session=session,
            graph_id=graph.id,
        )

        agents_with_id: Dict[str, str] = {
            agent.id: agent.name for agent in agents
        }

        base_model = GraphResponse.model_validate(graph)

        for edge in base_model.edges:
            from_node = edge.get("from_node")
            to_node = edge.get("to_node")

            if from_node in agents_with_id:
                edge["from_node"] = agents_with_id[from_node]

            if to_node in agents_with_id:
                edge["to_node"] = agents_with_id[to_node]

        node_names: List[str] = []

        node_names.extend(agents_with_id.values())

        if base_model.functions:
            node_names.extend(base_model.functions)

        node_names = list(dict.fromkeys(node_names))

        agent_models = [AgentResponse.model_validate(a) for a in agents]

        return base_model.model_copy(
            update={
                "agents": agent_models,
                "nodes": node_names,
            }
        )

    async def get_paginated_list_with_agent(
            self,
            session: AsyncSession,
            params: Optional[CustomParams] = None,
            sort: Optional[str] = None,
            **filters
    ) -> PaginationInfo[List[GraphResponse]]:
        items: List[GraphResponse] = []

        pages: Page[GraphTable] = await self._repository.paginate_by(
            session, params, sort, **filters
        )

        for graph in pages.items:
            items.append(await self._build_graph_response(session, graph))

        pagination_info = PaginationInfo.from_fastapi_page(items, pages)
        return pagination_info

    async def get_by_id_with_agent(self, session, _id) -> GraphResponse:
        graph = await self._repository.find_by_id(session, _id)
        if not graph:
            raise RuntimeError(f"Graph with id {_id} not found")
        return await self._build_graph_response(session, graph)

    async def delete_by_id_with_agent(
        self,
        session: AsyncSession,
        graph_id: str,
        commit: bool = True,
    ) -> bool:
        try:

            graph = await self._repository.find_by_id(session, graph_id)
            if graph is None:
                if commit:
                    await session.rollback()
                return False


            agents = await self._agent_repository.find_by(
                session=session,
                graph_id=graph.id,
            )
            agent_ids: List[str] = [a.id for a in agents]


            graph_deleted = await self._repository.delete_by_id(session, graph_id)


            agents_deleted = True
            if agent_ids:
                agents_deleted = await self._agent_repository.delete_in(
                    session,
                    agent_ids,
                )


            success = graph_deleted and agents_deleted


            if commit:
                if success:
                    await session.commit()
                else:
                    await session.rollback()

            return success

        except Exception:
            if commit:
                await session.rollback()
            raise

