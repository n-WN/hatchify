from datetime import datetime
from typing import Dict, Any, List

from pydantic import BaseModel, Field, ConfigDict

from app.common.domain.responses.agent_response import AgentResponse


class GraphResponse(BaseModel):
    id: str
    name: str
    description: str
    entry_point: str
    agents: List[AgentResponse] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    nodes: List[str] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
