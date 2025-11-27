from typing import List

from fastapi import APIRouter, Depends, Path
from loguru import logger
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.db.session import get_db
from app.business.manager.service_manager import ServiceManager
from app.business.models.graph import GraphTable
from app.business.services.graph_service import GraphService
from app.business.utils.pagination_utils import CustomParams
from app.common.domain.requests.graph import PageGraphRequest, UpdateGraphRequest
from app.common.domain.responses.graph_response import GraphResponse
from app.common.domain.responses.pagination import PaginationInfo
from app.common.domain.result.result import Result

graphs_router = APIRouter(prefix="/graphs")


@graphs_router.get("/get_by_id/{id}", response_model=Result[GraphResponse])
async def get_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: GraphService = Depends(ServiceManager.get_service_dependency(GraphService)),
):
    try:
        response: GraphResponse = await service.get_by_id_with_agent(session, _id)
        if not response:
            return Result.failed(
                code=404,
                message="Source Not Found",
            )
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

        page_info: PaginationInfo[List[GraphResponse]] = await service.get_paginated_list_with_agent(
            session, params, sort=list_request.sort
        )
        return Result.ok(data=page_info)
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
    try:
        update_data = update_request.model_dump(exclude_defaults=True, exclude_none=True)
        obj_tb: GraphTable = await service.update_by_id(session, _id, update_data)
        if not obj_tb:
            return Result.failed(code=500, message="Update Source Failed")
        response = GraphResponse.model_validate(obj_tb)
        return Result.ok(data=response)
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
        is_deleted: bool = await service.delete_by_id_with_agent(session, _id)
        if not is_deleted:
            return Result.failed(code=500, message="Delete Source Failed")
        return Result.ok(data=is_deleted)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)
