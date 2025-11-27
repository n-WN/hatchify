from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from app.common.domain.enums.agent_category import AgentCategory
from app.common.domain.requests.base import BasePageRequest


class PageAgentRequest(BasePageRequest):
    ...


class AddAgentRequest(BaseModel):
    name: str
    model: str
    instruction: str
    graph_id: str
    category: AgentCategory = Field(default=AgentCategory.GENERAL)
    structured_output_schema: Dict[str, Any]


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = Field(default=None)
    model: Optional[str] = Field(default=None)
    instruction: Optional[str] = Field(default=None)
    graph_id: Optional[str] = Field(default=None)
    category: Optional[AgentCategory] = Field(default=None)
    structured_output_schema: Optional[Dict[str, Any]] = Field(default=None)
