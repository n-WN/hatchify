import json
import mimetypes
from typing import Dict, Any, List, get_args, Optional

from pydantic import BaseModel
from strands.types.content import ContentBlock
from strands.types.media import DocumentFormat, ImageFormat, VideoFormat, DocumentContent, DocumentSource, ImageContent, \
    ImageSource, VideoContent, VideoSource

from app.common.domain.enums.storage_type import StorageType
from app.common.extensions.ext_storage import storage_client
from app.core.builder.graph_wrapper import GraphWrapper


class FileData(BaseModel):
    key: str
    mime: str
    name: str
    source: StorageType


class GraphExecuteData(BaseModel):
    jsons: Dict[str, Any]
    files: Dict[str, List[FileData]]


document_formats = get_args(DocumentFormat)
image_formats = get_args(ImageFormat)
video_formats = get_args(VideoFormat)


class GraphExecutor:

    def __init__(self, graph: GraphWrapper):
        self.graph = graph

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

                            )
                        )
                    )
                elif ext in image_formats:
                    messages.append(
                        ContentBlock(
                            text=f"This is images. `{field}.{index}` file data",
                            image=ImageContent(
                                format=ext,  # type: ignore
                                source=ImageSource(bytes=bytes_data)
                            )
                        )
                    )
                elif ext in video_formats:
                    messages.append(
                        ContentBlock(
                            text=f"This is videos. `{field}.{index}` file data",
                            video=VideoContent(
                                format=ext,  # type: ignore
                                source=VideoSource(bytes=bytes_data)
                            )
                        )
                    )
                else:
                    raise TypeError(f"Unsupported file format: {ext}")
        if task.jsons:
            messages.append(
                ContentBlock(text=f"User’s input: {json.dumps(task.jsons, indent=2, ensure_ascii=False)})")
            )
        return messages

    async def stream_async(
            self,
            task: GraphExecuteData,
            invocation_state: Dict[str, Any] | None = None,
            **kwargs: Any
    ):
        messages = await self.build_messages(task)

        async for event in self.graph.stream_async(messages, invocation_state, **kwargs):
            yield event

    async def invoke_async(
            self,
            task: GraphExecuteData,
            invocation_state: Dict[str, Any] | None = None,
            **kwargs: Any
    ):
        messages = await self.build_messages(task)

        result = await self.graph.invoke_async(messages, invocation_state, **kwargs)
        return result
