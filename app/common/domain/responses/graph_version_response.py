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
    session_id: str | None = Field(default=None)
    message_id: str | None = Field(default=None)

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
