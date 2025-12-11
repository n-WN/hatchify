from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    """Agent 对话事件包装"""
    data: Any
    type: Literal["agent"] = Field(default="agent", exclude=True)


class DeployEvent(BaseModel):
    """部署构建事件包装"""
    data: Any
    type: Literal["deploy"] = Field(default="deploy", exclude=True)
