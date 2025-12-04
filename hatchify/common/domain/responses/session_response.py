from datetime import datetime

from pydantic import BaseModel, ConfigDict

from hatchify.common.domain.enums.session_scene import SessionScene


class SessionResponse(BaseModel):
    id: str
    graph_id: str
    scene: SessionScene
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
