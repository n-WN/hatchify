from typing import List

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.db.session import get_db
from app.business.manager.service_manager import ServiceManager
from app.business.models.graph import GraphTable
from app.business.services.graph_service import GraphService
from app.business.utils.pagination_utils import CustomParams
from app.common.domain.requests.graph import (
    PageGraphRequest,
    UpdateGraphRequest,
    ConversationRequest,
)
from app.common.domain.responses.graph_response import GraphResponse
from app.common.domain.responses.graph_rollback_response import GraphRollbackResponse
from app.common.domain.responses.graph_spec_response import GraphSpecResponse
from app.common.domain.responses.graph_version_response import GraphVersionResponse
from app.common.domain.responses.pagination import PaginationInfo
from app.common.domain.result.result import Result
from app.core.graph.graph_spec_generator import GraphSpecGenerator
from app.core.manager.executor_manager import ExecutorManager
from app.core.manager.service_manager import ServiceManager as CoreServiceManager

graphs_router = APIRouter(prefix="/graphs")


@graphs_router.get("/get_by_id/{id}", response_model=Result[GraphResponse])
async def get_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    try:
        obj_tb: GraphTable = await service.get_by_id(session, _id)
        if not obj_tb:
            return Result.failed(
                code=404,
                message="Source Not Found",
            )
        response = GraphResponse.model_validate(obj_tb)
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@graphs_router.get("/page", response_model=Result[PaginationInfo[List[GraphResponse]]])
async def page(
        list_request: PageGraphRequest = Depends(),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    try:
        params = CustomParams(page=list_request.page, size=list_request.size)

        pages: Page[GraphTable] = await service.get_paginated_list(
            session, params, sort=list_request.sort
        )
        data = [GraphResponse.model_validate(item) for item in pages.items]
        page_info = PaginationInfo.from_fastapi_page(data=data, page_result=pages)
        return Result.ok(data=page_info)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@graphs_router.delete("/delete_by_id/{id}", response_model=Result[bool])
async def delete_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    try:
        is_deleted: bool = await service.delete_by_id(session, _id)
        if not is_deleted:
            return Result.failed(code=500, message="Delete Source Failed")
        return Result.ok(data=is_deleted)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@graphs_router.put("/update_by_id/{id}", response_model=Result[GraphResponse])
async def update_by_id(
        update_request: UpdateGraphRequest,
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    """
    更新 Graph
    - 可以更新 name, description, spec
    - 如果更新了 spec，current_version_id 会设为 NULL（标记有未保存修改）
    - 如果只更新 name/description，current_version_id 不变
    """
    try:
        update_data = update_request.model_dump(exclude_defaults=True, exclude_none=True)
        obj_tb: GraphTable = await service.update_by_id(session, _id, update_data)
        if not obj_tb:
            return Result.failed(code=500, message="Update Graph Failed")
        response = GraphResponse.model_validate(obj_tb)
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@graphs_router.post("/{id}/snapshot", response_model=Result[GraphVersionResponse])
async def create_snapshot(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    """为 Graph 创建快照版本"""
    try:
        version = await service.create_snapshot(session, _id)
        response = GraphVersionResponse.model_validate(version)
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@graphs_router.post("/{id}/rollback/{version_id}", response_model=Result[GraphRollbackResponse])
async def rollback_to_version(
        _id: str = Path(default=..., alias="id"),
        version_id: int = Path(default=...),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    """回滚到指定版本"""
    try:
        graph, branch_session_id = await service.rollback_to_version(session, _id, version_id)
        response = GraphRollbackResponse(
            graph=GraphResponse.model_validate(graph),
            branch_session_id=branch_session_id,
        )
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@graphs_router.post("/conversation/{session_id}")
async def conversation(
        request: ConversationRequest,
        session_id: str = Path(...),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    """通过自然语言对话编辑 Graph"""
    try:
        response = await service.conversation(session, session_id, request)
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg, exc_info=True)
        return Result.failed(code=500, message=msg)
