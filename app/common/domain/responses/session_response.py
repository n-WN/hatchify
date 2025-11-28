from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    id: str
    graph_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)