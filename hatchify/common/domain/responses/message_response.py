from datetime import datetime
from typing import List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from hatchify.common.domain.enums.message_role import MessageRole


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: MessageRole
    content: List[Dict[str, Any]]
    token_usage: Dict[str, Any] = Field(default_factory=dict)
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
