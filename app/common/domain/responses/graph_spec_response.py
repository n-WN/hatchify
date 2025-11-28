from typing import Any, Dict

from pydantic import BaseModel, Field


class GraphSpecResponse(BaseModel):
    graph_id: str = Field(..., description="Graph ID")
    spec: Dict[str, Any] = Field(..., description="当前 GraphSpec")
