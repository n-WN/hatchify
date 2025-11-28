import uuid
from typing import Literal, Any

from pydantic import BaseModel, Field


class StartEvent(BaseModel):
    type: Literal["start"] = Field(default="start", exclude=True)
    task_id: str


class PingEvent(BaseModel):
    type: Literal["ping"] = Field(default="ping", exclude=True)
    timestamp: int


class CancelEvent(BaseModel):
    type: Literal["cancel"] = Field(default="cancel", exclude=True)
    reason: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = Field(default="error", exclude=True)
    reason: str


class ResultEvent(BaseModel):
    type: Literal["result"] = Field(default="result", exclude=True)
    data: Any


class DoneEvent(BaseModel):
    type: Literal["done"] = Field(default="done", exclude=True)
    task_id: str
    reason: Literal["completed", "cancel", "error"]


class StreamEvent[T, D](BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: T
    data: D
