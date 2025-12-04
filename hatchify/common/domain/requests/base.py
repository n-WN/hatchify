from typing import Optional

from pydantic import BaseModel, Field


class BasePageRequest(BaseModel):
    """基础分页请求类，使用 base-1（从1开始）的页码"""
    page: int = Field(default=1)  # 页码，从1开始
    size: int = Field(default=10)  # 每页大小
    sort: Optional[str] = Field(default=None, description="field1:asc,field2:desc")
