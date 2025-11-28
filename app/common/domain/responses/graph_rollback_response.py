from typing import Optional

from pydantic import BaseModel, Field

from app.common.domain.responses.graph_response import GraphResponse


class GraphRollbackResponse(BaseModel):
    graph: GraphResponse = Field(..., description="回滚后的 Graph 状态")
    branch_session_id: Optional[str] = Field(
        default=None, description="用于继续对话的分支会话 ID（若存在）"
    )
