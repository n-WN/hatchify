import uuid
from typing import Literal, Any, Dict, TypeAlias, Union, List

from pydantic import BaseModel, Field
from strands.multiagent.base import Status


class StartEvent(BaseModel):
    graph_id: str
    type: Literal["start"] = Field(default="start", exclude=True)


class NodeStartEvent(BaseModel):
    node_id: str
    type: Literal["node_start"] = Field(default="node_start", exclude=True)


class NodeStopEvent(BaseModel):
    node_id: str
    status: Status = Field(default=Status.PENDING)
    result: Union[str, Dict[str, Any]]
    type: Literal["node_stop"] = Field(default="node_stop", exclude=True)


class NodeHandoffEvent(BaseModel):
    from_node_id: List[str]
    to_node_id: List[str]
    type: Literal["node_handoff"] = Field(default="node_handoff", exclude=True)


class CancelEvent(BaseModel):
    reason: str
    type: Literal["cancel"] = Field(default="cancel", exclude=True)


class ErrorEvent(BaseModel):
    reason: str
    type: Literal["error"] = Field(default="error", exclude=True)


class ResultEvent(BaseModel):
    status: Status = Field(default=Status.PENDING)
    results: Dict[str, Any]
    type: Literal["result"] = Field(default="result", exclude=True)


class DoneEvent(BaseModel):
    graph_id: str
    reason: Literal["completed", "cancel", "error"]
    type: Literal["done"] = Field(default="done", exclude=True)


class PingEvent(BaseModel):
    timestamp: int
    type: Literal["ping"] = Field(default="ping", exclude=True)


StreamEvent: TypeAlias = Union[
    StartEvent, NodeStartEvent, NodeStopEvent, NodeHandoffEvent, CancelEvent, ErrorEvent, ResultEvent, DoneEvent, PingEvent
]


class GraphEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: Literal[
        "start", "node_start", "node_stop", "node_handoff", "cancel", "error", "result", "done", "ping"
    ]
    data: StreamEvent
