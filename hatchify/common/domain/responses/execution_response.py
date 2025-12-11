from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from hatchify.common.domain.enums.execution_status import ExecutionStatus
from hatchify.common.domain.enums.execution_type import ExecutionType


class ExecutionResponse(BaseModel):
    """执行记录响应 DTO"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="执行ID")
    type: ExecutionType = Field(description="执行类型")
    status: ExecutionStatus = Field(description="执行状态")
    error: Optional[str] = Field(default=None, description="错误信息")
    graph_id: Optional[str] = Field(default=None, description="关联的 Graph ID")
    session_id: Optional[str] = Field(default=None, description="关联的会话 ID")
    created_at: datetime = Field(description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    updated_at: datetime = Field(description="更新时间")