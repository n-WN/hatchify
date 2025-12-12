from datetime import datetime
from typing import List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    @field_validator('token_usage', 'meta_data', mode='before')
    @classmethod
    def convert_none_to_dict(cls, v):
        """将 None 值转换为空字典"""
        return v if v is not None else {}
