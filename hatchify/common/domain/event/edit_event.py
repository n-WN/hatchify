from typing import Literal, Optional, Union, TypeAlias

from pydantic import BaseModel, Field

from hatchify.common.domain.event.base_event import PingEvent, DoneEvent, StartEvent, CancelEvent, ErrorEvent
from hatchify.common.domain.event.execute_event import ResultEvent


class PhaseEvent(BaseModel):
    type: Literal["phase"] = Field(default="phase", exclude=True)
    phase: Literal["prepare", "record", "generate", "extract", "merge"]
    message: Optional[str] = None


EditEventData: TypeAlias = Union[
    StartEvent,
    PingEvent,
    CancelEvent,
    ErrorEvent,
    ResultEvent,
    DoneEvent,
    PhaseEvent,
]
EditEventType = Literal[
    "start",
    "ping",
    "cancel",
    "error",
    "result",
    "done",
    "phase"
]
