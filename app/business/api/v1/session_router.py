from typing import List

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.db.session import get_db
from app.business.manager.service_manager import ServiceManager
from app.business.models.session import SessionTable
from app.business.services.session_service import SessionService
from app.business.utils.pagination_utils import CustomParams
from app.common.domain.requests.session import (
    PageSessionRequest
)
from app.common.domain.responses.pagination import PaginationInfo
from app.common.domain.responses.session_response import SessionResponse
from app.common.domain.result.result import Result

sessions_router = APIRouter(prefix="/sessions")


@sessions_router.get("/get_by_id/{id}", response_model=Result[SessionResponse])
async def get_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: SessionService = Depends(ServiceManager.get_service_dependency(SessionService)),
):
    try:
        obj_tb: SessionTable = await service.get_by_id(session, _id)
        if not obj_tb:
            return Result.failed(
                code=404,
                message="Session Not Found",
            )
        response = SessionResponse.model_validate(obj_tb)
        return Result.ok(data=response)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@sessions_router.get("/page", response_model=Result[PaginationInfo[List[SessionResponse]]])
async def page(
        list_request: PageSessionRequest = Depends(),
        session: AsyncSession = Depends(get_db),
        service: SessionService = Depends(ServiceManager.get_service_dependency(SessionService)),
):
    try:
        params = CustomParams(page=list_request.page, size=list_request.size)

        # 构建过滤条件
        filters = {}
        if list_request.graph_id:
            filters["graph_id"] = list_request.graph_id
        if list_request.scene:
            filters["scene"] = list_request.scene

        pages: Page[SessionTable] = await service.get_paginated_list(
            session, params, sort=list_request.sort, **filters
        )
        data = [SessionResponse.model_validate(item) for item in pages.items]
        page_info = PaginationInfo.from_fastapi_page(data=data, page_result=pages)
        return Result.ok(data=page_info)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)


@sessions_router.delete("/delete_by_id/{id}", response_model=Result[bool])
async def delete_by_id(
        _id: str = Path(default=..., alias="id"),
        session: AsyncSession = Depends(get_db),
        service: SessionService = Depends(ServiceManager.get_service_dependency(SessionService)),
):
    try:
        is_deleted: bool = await service.delete_by_id(session, _id)
        if not is_deleted:
            return Result.failed(code=500, message="Delete Session Failed")
        return Result.ok(data=is_deleted)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)}"
        logger.error(msg)
        return Result.failed(code=500, message=msg)
