from typing import Optional

from pydantic import Field

from hatchify.common.domain.enums.execution_status import ExecutionStatus
from hatchify.common.domain.enums.execution_type import ExecutionType
from hatchify.common.domain.requests.base import BasePageRequest


class PageExecutionRequest(BasePageRequest):
    """分页查询执行记录请求"""

    graph_id: Optional[str] = Field(default=None, description="筛选：Graph ID")
    session_id: Optional[str] = Field(default=None, description="筛选：会话 ID")
    status: Optional[ExecutionStatus] = Field(default=None, description="筛选：执行状态")
    type: Optional[ExecutionType] = Field(default=None, description="筛选：执行类型")