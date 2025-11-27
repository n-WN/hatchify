from abc import ABC, abstractmethod
from typing import Type, Any, Generic, Collection, Optional

from fastapi_pagination import Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.db.base import T
from app.business.utils.pagination_utils import CustomParams


class BaseService(Generic[T], ABC):
    def __init__(self, entity_type: Type[T]):
        self.entity_type = entity_type

    @abstractmethod
    async def get_by_id(
            self,
            session: AsyncSession,
            entity_id: Any
    ) -> Optional[T]:
        ...

    @abstractmethod
    async def get_all(
            self,
            session: AsyncSession,
            offset: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None
    ) -> Collection[T]:
        ...

    @abstractmethod
    async def get_list(
            self,
            session: AsyncSession,
            offset: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[str] = None,
            **filters
    ) -> Collection[T]:
        ...

    @abstractmethod
    async def count(
            self,
            session: AsyncSession,
            **filters
    ) -> int:
        ...

    @abstractmethod
    async def create(
            self,
            session: AsyncSession,
            entity_data: dict,
            commit: bool = True
    ) -> T:
        ...

    @abstractmethod
    async def batch_create(
            self,
            session: AsyncSession,
            entities_data: list[dict],
            commit: bool = True
    ) -> Collection[T]:
        ...

    @abstractmethod
    async def update_by_id(
            self,
            session: AsyncSession,
            entity_id: Any,
            update_data: dict,
            commit: bool = True
    ) -> Optional[T]:
        ...

    @abstractmethod
    async def delete_by_id(
            self,
            session: AsyncSession,
            entity_id: Any,
            commit: bool = True
    ) -> bool:
        ...

    async def get_paginated(
            self,
            session: AsyncSession,
            params: Optional[CustomParams] = None,
            sort: Optional[str] = None
    ) -> Page[T]:
        ...

    async def get_paginated_list(
            self,
            session: AsyncSession,
            params: Optional[CustomParams] = None,
            sort: Optional[str] = None,
            **filters
    ) -> Page[T]:
        ...
