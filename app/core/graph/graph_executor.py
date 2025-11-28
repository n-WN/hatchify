import asyncio
import json
import mimetypes
import time
from typing import Dict, Any, List, get_args, Optional, Union, Literal

from loguru import logger
from strands.agent import AgentResult
from strands.multiagent.base import NodeResult, MultiAgentResult
from strands.types.content import ContentBlock
from strands.types.media import DocumentFormat, ImageFormat, VideoFormat, DocumentContent, DocumentSource, ImageContent, \
    ImageSource, VideoContent, VideoSource

from app.common.domain.entity.graph_execute_data import GraphExecuteData
from app.common.event.stream_event import NodeStartEvent, GraphEvent, NodeStopEvent, NodeHandoffEvent, ResultEvent, \
    StartEvent, DoneEvent, CancelEvent, ErrorEvent, PingEvent
from app.common.extensions.ext_storage import storage_client
from app.core.graph.graph_wrapper import GraphWrapper
from app.core.manager.event_manager import EventStore

document_formats = get_args(DocumentFormat)
image_formats = get_args(ImageFormat)
video_formats = get_args(VideoFormat)


class GraphExecutor:

    def __init__(
            self,
            graph_id: str,
            graph: GraphWrapper,
            ping_interval: int = 15,
            enable_reconnect: bool = True,
            event_ttl: int = 3600
    ):
        self.graph_id = graph_id
        self.graph = graph
        self.stream_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self.stream_queue: asyncio.Queue[GraphEvent] = asyncio.Queue()
        self.stored_exception: Optional[Exception] = None
        self.ping_interval = ping_interval
        self.ping_running = False
        self.enable_reconnect = enable_reconnect
        self.event_ttl = event_ttl
        self.event_store: Optional[EventStore] = None

    @staticmethod
    async def build_messages(
            task: GraphExecuteData,
    ) -> List[ContentBlock]:
        messages: List[ContentBlock] = []
        for field, sub_files in task.files.items():
            for index, sub_file in enumerate(sub_files):

                ext_with_dot: Optional[str] = mimetypes.guess_extension(sub_file.mime)
                if ext_with_dot is None:
                    raise RuntimeError(f"Unsupported file format: {sub_file.name}")
                ext = ext_with_dot.split(".")[-1]
                bytes_data: bytes = await storage_client.load(sub_file.key)

                if ext in document_formats:
                    messages.append(
                        ContentBlock(
                            text=f"This is files. `{field}.{index}` file data",
                            document=DocumentContent(
                                format=ext,  # type: ignore
                                name=sub_file.name,
                                source=DocumentSource(bytes=bytes_data)

                            ),
                            source_key=sub_file.key  # type: ignore 自定义额外字段，用于配合重写后的 FileSessionManager
                        )
                    )
                elif ext in image_formats:
                    messages.append(
                        ContentBlock(
                            text=f"This is images. `{field}.{index}` file data",
                            image=ImageContent(
                                format=ext,  # type: ignore
                                source=ImageSource(bytes=bytes_data)
                            ),
                            source_key=sub_file.key  # type: ignore 自定义额外字段，用于配合重写后的 FileSessionManager
                        )
                    )
                elif ext in video_formats:
                    messages.append(
                        ContentBlock(
                            text=f"This is videos. `{field}.{index}` file data",
                            video=VideoContent(
                                format=ext,  # type: ignore
                                source=VideoSource(bytes=bytes_data)
                            ),
                            source_key=sub_file.key  # type: ignore 自定义额外字段，用于配合重写后的 FileSessionManager
                        )
                    )
                else:
                    raise TypeError(f"Unsupported file format: {ext}")
        if task.jsons:
            messages.append(
                ContentBlock(text=f"User’s input: {json.dumps(task.jsons, indent=2, ensure_ascii=False)})")
            )
        return messages

    async def handle_stream_event(self, event: Dict[str, Any]):
        event_type = event.get("type")
        if event_type in ["multiagent_node_stream"]:
            return
        match event_type:
            case "multiagent_node_start":
                await self.stream_queue.put(
                    GraphEvent(
                        type="node_start",
                        data=NodeStartEvent(
                            node_id=event.get("node_id"),
                        )
                    )
                )
            case "multiagent_node_stop":
                node_result: NodeResult = event.get("node_result")
                result = node_result.result
                if isinstance(result, AgentResult):
                    await self.stream_queue.put(
                        GraphEvent(
                            type="node_stop",
                            data=NodeStopEvent(
                                node_id=event.get("node_id"),
                                status=node_result.status,
                                result=result.structured_output.model_dump() or str(result)
                            )
                        )
                    )
            case "multiagent_handoff":
                await self.stream_queue.put(
                    GraphEvent(
                        type="node_handoff",
                        data=NodeHandoffEvent(
                            to_node_id=event.get("node_id", []),
                            from_node_id=event.get("from_node_ids", []),
                        )
                    )
                )
            case "multiagent_result":
                result_dict: Dict[str, Union[str, Dict[str, Any]]] = {}
                multi_agent_result: MultiAgentResult = event.get("result")
                for node_id, node_result in multi_agent_result.results.items():
                    result = node_result.result
                    if isinstance(result, AgentResult):
                        result_dict[node_id] = result.structured_output.model_dump() or str(result)
                await self.stream_queue.put(
                    GraphEvent(
                        type="result",
                        data=ResultEvent(
                            status=multi_agent_result.status,
                            results=result_dict,
                        )
                    )
                )
            case _:
                raise TypeError(f"Unsupported event type: {event_type}")

    async def ping_loop(self):
        try:
            while self.ping_running:
                await asyncio.sleep(self.ping_interval)
                if self.ping_running:
                    await self.stream_queue.put(
                        GraphEvent(
                            type="ping",
                            data=PingEvent(
                                timestamp=int(time.time())
                            )
                        )
                    )
        except asyncio.CancelledError:
            logger.debug(f"Ping task cancelled for graph: {self.graph_id}")
        except Exception as e:
            logger.error(f"Ping task error: {type(e).__name__}: {e}")

    async def start_ping(self):
        if not self.ping_running:
            self.ping_running = True
            self.ping_task = asyncio.create_task(self.ping_loop())

    async def stop_ping(self):
        if not self.ping_running:
            return

        self.ping_running = False
        if self.ping_task:
            self.cancel_tasks(self.ping_task)
            await self.await_task_safely(self.ping_task)

    async def start_streaming(
            self,
            messages: List[ContentBlock],
            invocation_state: Dict[str, Any] | None = None,
            **kwargs: Any
    ):
        done_reason: Literal["completed", "cancel", "error"] = "completed"

        try:
            await self.stream_queue.put(
                GraphEvent(
                    type="start",
                    data=StartEvent(
                        graph_id=self.graph_id,
                    )
                )
            )
            async for event in self.graph.stream_async(messages, invocation_state, **kwargs):
                await self.handle_stream_event(event)
        except asyncio.CancelledError as e:
            # 客户端断开连接是正常行为，使用 info 级别
            msg = f"Stream cancelled (client disconnected or task stopped)"
            logger.info(f"{msg} - graph_id: {self.graph_id}")
            await self.stream_queue.put(
                GraphEvent(
                    type="cancel",
                    data=CancelEvent(
                        reason=msg
                    ),
                )
            )
            done_reason = "cancel"
            self.stored_exception = e
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            logger.error(msg)
            await self.stream_queue.put(
                GraphEvent(
                    type="error",
                    data=ErrorEvent(
                        reason=msg
                    ),
                )
            )
            done_reason = "error"
            self.stored_exception = e
        finally:
            await self.stop_ping()

            await self.stream_queue.put(
                GraphEvent(
                    type="done",
                    data=DoneEvent(
                        graph_id=self.graph_id,
                        reason=done_reason
                    ),
                )
            )

    async def send_terminal_events(
            self,
            terminal_type: Literal["error"],
            message: str,
            reason: Literal["error"]
    ):
        await self.stream_queue.put(
            GraphEvent(
                type="start",
                data=StartEvent(
                    graph_id=self.graph_id,
                ),
            )
        )

        if terminal_type == "error":  # error
            await self.stream_queue.put(
                GraphEvent(
                    type="error",
                    data=ErrorEvent(reason=message),
                )
            )
        else:
            raise TypeError(f"Unknown terminal type: {terminal_type}")

        # 在发送 DoneEvent 之前停止 ping
        await self.stop_ping()

        await self.stream_queue.put(
            GraphEvent(
                type="done",
                data=DoneEvent(
                    graph_id=self.graph_id,
                    reason=reason
                ),
            )
        )

    async def run_streamed(
            self,
            task: GraphExecuteData,
            invocation_state: Dict[str, Any] | None = None,
            **kwargs: Any
    ):
        try:
            messages = await self.build_messages(task)
            self.stream_task = asyncio.create_task(self.start_streaming(messages, invocation_state, **kwargs))
        except Exception as e:
            logger.error(f"Initialization failed: {type(e).__name__}: {e}")
            try:
                await self.send_terminal_events("error", f"{type(e).__name__}: {e}", "error")
            except Exception as inner_e:
                logger.error(f"Failed to send error events: {inner_e}")

    async def stream_events(self):
        is_complete: bool = False
        try:
            while True:
                if is_complete and self.stream_queue.empty():
                    break

                try:
                    event = await self.stream_queue.get()
                except asyncio.CancelledError:
                    break

                yield event
                self.stream_queue.task_done()

                if isinstance(event.data, DoneEvent):
                    is_complete = True

        finally:
            if self.stored_exception:
                raise self.stored_exception

    @staticmethod
    def cancel_tasks(asyncio_task: asyncio.Task) -> None:
        if not asyncio_task:
            return
        if asyncio_task is asyncio.current_task():
            return
        if not asyncio_task.done():
            asyncio_task.cancel()

    @staticmethod
    async def await_task_safely(asyncio_task: asyncio.Task) -> None:
        if not asyncio_task:
            return
        if asyncio_task is asyncio.current_task():
            return

        try:
            if not asyncio_task.done():
                await asyncio_task
            else:
                asyncio_task.result()
        except (asyncio.CancelledError, Exception) as e:
            logger.debug(f"{asyncio_task.get_name()} completed: {type(e).__name__}")

    async def worker(self, last_event_id: Optional[str] = None):
        try:
            if self.enable_reconnect:
                self.event_store = await EventStore.get_or_create(
                    self.graph_id,
                    ttl_seconds=self.event_ttl
                )

                if last_event_id:
                    logger.info(f"Reconnect request with last_event_id: {last_event_id}")
                    historical_events = self.event_store.get_after(last_event_id)

                    for event in historical_events:
                        yield self.format_sse(event)

                    if self.event_store.is_completed():
                        return

            await self.start_ping()
            async for event in self.stream_events():
                if self.enable_reconnect and self.event_store:
                    self.event_store.append(event)

                yield self.format_sse(event)

        except asyncio.CancelledError as e:
            logger.debug(f"worker cancelled: {self.graph_id}")
            raise e
        except Exception as e:
            logger.exception(f"{type(e).__name__}: {e}")
        finally:
            await self.stop_ping()

            if self.stream_task:
                self.cancel_tasks(self.stream_task)
                await self.await_task_safely(self.stream_task)

    @staticmethod
    def format_sse(event: GraphEvent) -> str:
        return "\n".join([
            f"id: {event.id}",
            f"event: {event.type}",
            f"data: {event.data.model_dump_json(exclude_none=True)}",
            "",
            ""
        ])

    async def invoke_async(
            self,
            task: GraphExecuteData,
            invocation_state: Dict[str, Any] | None = None,
            **kwargs: Any
    ):
        messages = await self.build_messages(task)

        result = await self.graph.invoke_async(messages, invocation_state, **kwargs)
        return result
