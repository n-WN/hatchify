from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from app.common.domain.entity.agent_node_spec import AgentNode
from app.common.domain.entity.function_node_spec import FunctionNode


class Edge(BaseModel):
    """Graph 边定义"""
    from_node: str = Field(..., description="起始节点名称")
    to_node: str = Field(..., description="目标节点名称")



class GraphSpec(BaseModel):
    """完整的 Graph 定义规范"""
    name: str = Field(..., description="Graph 名称")
    description: str = Field(
        default="",
        description="Graph 描述"
    )
    agents: List[AgentNode] = Field(
        default_factory=list,
        description="Agent 节点列表"
    )
    functions: List[FunctionNode] = Field(
        default_factory=list,
        description="Function 节点列表（确定性函数节点）"
    )
    nodes: List[str] = Field(
        ...,
        description="所有节点名称列表（agents + functions 的所有节点名）"
    )
    edges: List[Edge] = Field(
        ...,
        description="边列表，定义节点之间的连接关系"
    )
    entry_point: str = Field(
        ...,
        description="入口节点名称（第一个执行的节点）"
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Graph 输入 JSON Schema（用于前端表单生成和输入验证）\n"
            "- 文件字段应标记为 format: 'binary'\n"
            "- Webhook 处理方式（JSON vs Multipart）会根据 schema 自动推断\n"
            "- 如果存在 format: 'binary' 字段 → 使用 multipart/form-data\n"
            "- 否则 → 使用 application/json"
        )
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="由终端节点解析"
    )
