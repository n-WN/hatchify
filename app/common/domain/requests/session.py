from typing import Optional

from pydantic import BaseModel, Field

from app.common.domain.requests.base import BasePageRequest
from app.common.domain.enums.session_scene import SessionScene


class PageSessionRequest(BasePageRequest):
    graph_id: Optional[str] = Field(default=None, description="按 graph_id 过滤")
    scene: Optional[SessionScene] = Field(default=None, description="按 scene 过滤")


class AddSessionRequest(BaseModel):
    graph_id: str = Field(..., description="所属的图 ID")
    scene: Optional[SessionScene] = Field(
        default=SessionScene.GRAPH_EDIT,
        description="用途场景"
    )


class UpdateSessionRequest(BaseModel):
    graph_id: Optional[str] = Field(default=None, description="所属的图 ID")
    scene: Optional[SessionScene] = Field(default=None, description="用途场景")
