from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GraphVersionResponse(BaseModel):
    id: int
    graph_id: str
    version: int
    spec: dict
    session_id: str | None
    message_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)