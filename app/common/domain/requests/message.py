from typing import Optional

from pydantic import BaseModel, Field

from app.common.domain.enums.message_role import MessageRole
from app.common.domain.requests.base import BasePageRequest


class PageMessageRequest(BasePageRequest):
    session_id: Optional[str] = Field(default=None, description="按 session_id 过滤")
    role: Optional[MessageRole] = Field(default=None, description="按角色过滤")


class AddMessageRequest(BaseModel):
    session_id: str = Field(..., description="所属会话 ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class UpdateMessageRequest(BaseModel):
    role: Optional[MessageRole] = Field(default=None, description="消息角色")
    content: Optional[str] = Field(default=None, min_length=1, description="消息内容")