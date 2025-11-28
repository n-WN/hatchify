from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.domain.enums.graph_version_type import GraphVersionType


class GraphVersionResponse(BaseModel):
    id: int
    graph_id: str
    version: int | None
    type: GraphVersionType
    spec: dict
    comment: str | None = Field(default=None)
    parent_version_id: int | None = Field(default=None)
    branch_session_id: str | None = Field(default=None)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
