from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.domain.enums.message_role import MessageRole


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: MessageRole
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)