from typing import Any, List, Optional

from loguru import logger
from strands import Agent
from strands.types.content import Messages, ContentBlock, Message
from strands.types.tools import ToolUse, ToolResult

from hatchify.common.domain.event.base_event import StreamEvent
from hatchify.common.domain.event.web_build_event import DeltaEvent, ToolOutputEvent, ToolCallEvent, ToolCallItem
from hatchify.common.domain.event.wrapper_event import AgentEvent, DeployEvent
from hatchify.common.domain.requests.web_builder import WebBuilderConversationRequest
from hatchify.core.stream_handler.deploy import DeployGenerator
from hatchify.core.stream_handler.event_listener.event_listener import EventListener
from hatchify.core.stream_handler.stream_handler import BaseStreamHandler


class WebBuilderGenerator(BaseStreamHandler):

    def __init__(
            self,
            source_id: str,
            agent: Agent,
            project_path: str,
            redeploy: bool,
            listeners: Optional[List[EventListener]] = None,
    ):
        super().__init__(source_id=source_id, listeners=listeners)
        self.agent = agent
        self.project_path = project_path
        self.redeploy = redeploy

    async def handle_stream_event(self, event: Any):

        if isinstance(event, AgentEvent):
            if "message" in event.data:
                message: Message = event.data.get('message', {})
                content: List[ContentBlock] = message.get('content', [])
                tool_uses: List[ToolUse] = [c.get('toolUse') for c in content if c.get('toolUse')]
                tool_results: List[ToolResult] = [c.get('toolResult') for c in content if c.get('toolResult')]
                if tool_uses and not tool_results:
                    tool_call_item = []
                    for tool_use in tool_uses:
                        tool_call_id = tool_use.get("toolUseId")
                        name = tool_use.get("name")
                        args_override = {}

                        match name:
                            case "file_read":
                                args_override = {
                                    "path": tool_use.get("input").get("path")
                                }
                            case "image_reader":
                                args_override = {
                                    "path": tool_use.get("input").get("image_path")
                                }
                            case "editor":
                                args_override = {
                                    "path": tool_use.get("input").get("path")
                                }
                            case "file_write":
                                args_override = {
                                    "path": tool_use.get("input").get("path")
                                }
                            case "shell":
                                args_override = {
                                    "command": tool_use.get("input").get("command")
                                }
                            case _:
                                logger.error(f"please note!!! Unexpected tool_use: {name}")
                        tool_call_item.append(
                            ToolCallItem(tool_call_id=tool_call_id, tool_name=name, args=args_override))

                    await self.emit_event(
                        StreamEvent(
                            type='tool_call',
                            data=ToolCallEvent(
                                tool_calls=tool_call_item
                            )
                        )
                    )
                elif tool_results and not tool_uses:
                    for tool_result in tool_results:
                        tool_use_id = tool_result.get("toolUseId")
                        status = tool_result.get("status")
                        await self.emit_event(
                            StreamEvent(
                                type='tool_output',
                                data=ToolOutputEvent(
                                    tool_call_id=tool_use_id,
                                    status=status
                                )
                            )
                        )
                else:
                    logger.error(
                        f"Please note!!! Unexpected events tool_uses: {tool_uses}, tool_results: {tool_results}")

            if "data" in event.data:
                await self.emit_event(
                    StreamEvent(
                        type='delta',
                        data=DeltaEvent(
                            content=event.data.get('data'),
                        )
                    )
                )

        elif isinstance(event, DeployEvent):
            await self.emit_event(event.data)

    async def async_wrapper_generator(self, request: WebBuilderConversationRequest):
        messages: Messages = request.messages
        async_generator = self.agent.stream_async(messages)
        async for event in async_generator:
            yield AgentEvent(data=event)

        if self.redeploy:
            deploy_stream_handler = DeployGenerator(
                source_id=self.source_id,
                graph_id=request.graph_id,
                project_path=self.project_path,
                rebuild=request.redeploy,
                listeners=self.listeners,
            )
            deploy_generator = deploy_stream_handler.build_project()
            async for event in deploy_generator:
                yield DeployEvent(data=event)

    async def submit_task(
            self,
            request: WebBuilderConversationRequest,
    ):
        """
        提交任务并开始流式处理

        Args:
            request: Web Builder 对话请求
        """
        async_generator = self.async_wrapper_generator(request)
        await self.run_streamed(async_generator)
