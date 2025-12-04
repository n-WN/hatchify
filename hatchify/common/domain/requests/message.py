from typing import Optional

from pydantic import Field

from hatchify.common.domain.enums.message_role import MessageRole
from hatchify.common.domain.requests.base import BasePageRequest


class PageMessageRequest(BasePageRequest):
    session_id: Optional[str] = Field(default=None, description="按 session_id 过滤")
    role: Optional[MessageRole] = Field(default=None, description="按角色过滤")
