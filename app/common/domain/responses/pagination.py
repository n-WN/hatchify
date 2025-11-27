from typing import Self, TypeVar, List

from pydantic import BaseModel, Field

L = TypeVar('L', bound=List)


class PaginationInfo[L](BaseModel):
    page: int = Field(..., ge=1, description="当前页码（从1开始）")
    limit: int = Field(..., ge=1, le=10000, description="每页项目数量")
    total: int = Field(..., ge=0, description="总项目数量")
    pages: int = Field(..., ge=0, description="总页数")
    hasNext: bool = Field(..., description="是否有下一页")
    hasPrev: bool = Field(..., description="是否有上一页")
    list: L

    @classmethod
    def from_fastapi_page(cls, data: L, page_result) -> Self:
        return cls(
            page=page_result.page,  # 保持从1开始
            limit=page_result.size,
            total=page_result.total,
            pages=page_result.pages,
            hasNext=page_result.page < page_result.pages,
            hasPrev=page_result.page > 1,
            list=data
        )

    def to_dict(self) -> dict:
        return {
            "page": self.page,
            "limit": self.limit,
            "total": self.total,
            "pages": self.pages,
            "hasNext": self.hasNext,
            "hasPrev": self.hasPrev,
            "list": self.list
        }
