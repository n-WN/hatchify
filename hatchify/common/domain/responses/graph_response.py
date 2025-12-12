from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class GraphResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = Field(default=None)
    current_spec: Dict[str, Any]
    current_version_id: Optional[int] = Field(default=None)
    current_session_id: Optional[str] = Field(default=None)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
