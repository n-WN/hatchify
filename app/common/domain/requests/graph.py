from typing import Optional

from pydantic import BaseModel, Field
from strands.types.content import Messages

from app.common.domain.requests.base import BasePageRequest


class PageGraphRequest(BasePageRequest):
    ...


class AddGraphRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="图的名称")
    description: Optional[str] = Field(default=None, description="图的描述")
    spec: dict = Field(default_factory=dict, description="初始 spec（默认为空字典）")


class UpdateGraphRequest(BaseModel):
    """
    更新 Graph 请求
    - 如果更新了 spec，current_version_id 会设为 NULL（标记有未保存修改）
    - 如果只更新 name/description，current_version_id 不变
    """
    name: Optional[str] = Field(default=None, description="图的名称")
    description: Optional[str] = Field(default=None, description="图的描述")
    spec: Optional[dict] = Field(default=None, description="图的 spec")


class ConversationRequest(BaseModel):
    messages: Messages
