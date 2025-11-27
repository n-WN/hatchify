from datetime import datetime
from typing import Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from app.common.domain.enums.agent_category import AgentCategory


class AgentResponse(BaseModel):
    id: str
    name: str
    model: str
    instruction: str
    category: AgentCategory
    graph_id: str
    structured_output_schema: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
