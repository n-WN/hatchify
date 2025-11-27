from typing import List

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page
from loguru import logger
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.db.session import get_db
from app.business.manager.service_manager import ServiceManager
from app.business.models.agent import AgentTable
from app.business.services.agent_service import AgentService
from app.business.utils.pagination_utils import CustomParams
from app.common.domain.requests.agent import PageAgentRequest, UpdateAgentRequest
from app.common.domain.responses.agent_response import AgentResponse
from app.common.domain.responses.pagination import PaginationInfo
from app.common.domain.result.result import Result

agents_router = APIRouter(prefix="/agents")


@agents_router.get("/get_by_id/{id}", response_model=Result[AgentResponse])
async def get_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: AgentService = Depends(ServiceManager.get_service_dependency(AgentService)),
):
    try:
        tb_obj: AgentTable = await service.get_by_id(session, _id)
        if not tb_obj:
            return Result.failed(
                code=404,
                message="Source Not Found",
            )
        graph_response = AgentResponse.model_validate(tb_obj)
        return Result.ok(data=graph_response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@agents_router.get("/page", response_model=Result[PaginationInfo[List[AgentResponse]]])
async def page(
        list_request: PageAgentRequest = Depends(),
        session: AsyncSession = Depends(get_db),
        service: AgentService = Depends(ServiceManager.get_service_dependency(AgentService)),
):
    try:
        params = CustomParams(page=list_request.page, size=list_request.size)

        page_result: Page[AgentTable] = await service.get_paginated_list(
            session, params, sort=list_request.sort
        )

        result = [
            AgentResponse.model_validate(item)
            for item in page_result.items
        ]
        pagination_info = PaginationInfo.from_fastapi_page(result, page_result)
        return Result.ok(data=pagination_info)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@agents_router.put("/update_by_id/{id}", response_model=Result[AgentResponse])
async def update_by_id(
        update_request: UpdateAgentRequest,
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: AgentService = Depends(ServiceManager.get_service_dependency(AgentService)),
):
    try:
        update_data = update_request.model_dump(exclude_defaults=True, exclude_none=True)
        obj_tb: AgentTable = await service.update_by_id(session, _id, update_data)
        if not obj_tb:
            return Result.failed(code=500, message="Update Source Failed")
        response = AgentResponse.model_validate(obj_tb)
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@agents_router.delete("/delete_by_id/{id}", response_model=Result[bool])
async def delete_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: AgentService = Depends(ServiceManager.get_service_dependency(AgentService)),
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
