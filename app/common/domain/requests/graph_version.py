from typing import Optional

from pydantic import BaseModel, Field

from app.common.domain.requests.base import BasePageRequest
from app.common.domain.enums.graph_version_type import GraphVersionType


class PageGraphVersionRequest(BasePageRequest):
    graph_id: Optional[str] = Field(default=None, description="按 graph_id 过滤")


class AddGraphVersionRequest(BaseModel):
    """
    创建新版本请求。
    version 号会由系统自动计算（max(version) + 1）
    """
    graph_id: str = Field(..., description="所属的图 ID")
    spec: dict = Field(..., description="完整的 graph spec（JSON）")
    session_id: Optional[str] = Field(default=None, description="所属会话 ID")
    message_id: Optional[str] = Field(
        default=None,
        description="触发的消息 ID"
    )
    type: GraphVersionType = Field(
        default=GraphVersionType.SNAPSHOT,
        description="快照类型"
    )


class UpdateGraphVersionRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="所属会话 ID")
    message_id: Optional[str] = Field(
        default=None,
        description="触发的消息 ID"
    )
    spec: dict = Field(..., description="完整的 graph spec（JSON）")
