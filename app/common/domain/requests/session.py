from typing import Optional

from pydantic import BaseModel, Field

from app.common.domain.requests.base import BasePageRequest


class PageSessionRequest(BasePageRequest):
    graph_id: Optional[str] = Field(default=None, description="按 graph_id 过滤")


class AddSessionRequest(BaseModel):
    graph_id: str = Field(..., description="所属的图 ID")


class UpdateSessionRequest(BaseModel):
    graph_id: Optional[str] = Field(default=None, description="所属的图 ID")