from typing import Literal, Any, Dict, TypeAlias, Union, List

from pydantic import BaseModel, Field
from strands.multiagent.base import Status

from app.common.event.base_event import StartEvent, CancelEvent, ErrorEvent, DoneEvent, PingEvent, ResultEvent


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


ExecuteEventData: TypeAlias = Union[
    StartEvent,
    PingEvent,
    CancelEvent,
    ErrorEvent,
    ResultEvent,
    DoneEvent,
    NodeStartEvent,
    NodeStopEvent,
    NodeHandoffEvent
]
ExecuteEventType: TypeAlias = Literal[
    "start",
    "ping",
    "cancel",
    "error",
    "result",
    "done",
    "node_start",
    "node_stop",
    "node_handoff"
]
