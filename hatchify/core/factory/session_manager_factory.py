import asyncio
import copy
import json
import mimetypes
import os.path
import threading
import uuid
from typing import cast, Any, Optional
from typing import get_args

from strands.session import FileSessionManager, SessionManager, RepositorySessionManager
from strands.types.exceptions import SessionException
from strands.types.media import DocumentFormat, ImageFormat, VideoFormat

from hatchify.common.domain.enums.session_manager_type import SessionManagerType
from hatchify.common.extensions.ext_storage import storage_client
from hatchify.common.settings.settings import get_hatchify_settings

settings = get_hatchify_settings()
document_formats = get_args(DocumentFormat)
image_formats = get_args(ImageFormat)
video_formats = get_args(VideoFormat)


class BinarySafeFileSessionManager(FileSessionManager):
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _loop_thread: Optional[threading.Thread] = None
    _loop_lock = threading.Lock()

    @classmethod
    def _ensure_loop(cls) -> asyncio.AbstractEventLoop:
        if cls._loop is None:
            with cls._loop_lock:

                if cls._loop is None:
                    new_loop = asyncio.new_event_loop()

                    def run_loop():
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_forever()

                    thread = threading.Thread(target=run_loop, daemon=True, name="BinaryLoadLoop")
                    thread.start()

                    cls._loop = new_loop
                    cls._loop_thread = thread

        return cls._loop

    def __init__(
            self,
            graph_id: str,
            session_id: str,
            storage_dir: Optional[str] = None,
            **kwargs: Any,
    ):
        super().__init__(session_id, storage_dir, **kwargs)
        self.graph_id = graph_id
        self._ensure_loop()

    @staticmethod
    async def overload_binary_messages(tasks: list[dict[str, Any]]) -> None:
        for task in tasks:
            if source_key := task.get("source_key"):
                bytes_data: bytes = await storage_client.load(source_key)
                if document := task.get("document"):
                    if source := document.get("source"):
                        source["bytes"] = bytes_data
                elif image := task.get("image"):
                    if source := image.get("source"):
                        source["bytes"] = bytes_data
                elif video := task.get("video"):
                    if source := video.get("source"):
                        source["bytes"] = bytes_data

    async def update_binary_data(self, data: dict[str, Any]) -> dict[str, Any]:
        data_to_write = copy.deepcopy(data)
        current_task = data_to_write.get("current_task", [])

        for task in current_task:
            # 处理已有 source_key 的任务,只需移除 bytes
            if task.get("source_key"):
                for content_type in ["document", "image", "video"]:
                    if content := task.get(content_type):
                        if source := content.get("source"):
                            source.pop("bytes", None)
            else:
                # 处理没有 source_key 的任务,需要保存二进制数据
                for content_type in ["document", "image", "video"]:
                    if content := task.get(content_type):
                        content_format = content.get("format")
                        if not content_format:
                            continue

                        mime_type = mimetypes.types_map.get(f".{content_format}") or "application/octet-stream"

                        if source := content.get("source"):
                            if bytes_data := source.pop("bytes", None):
                                key = f"{self.graph_id}/hatchify__{uuid.uuid4().hex}.{content_format}"
                                await storage_client.save(key=key, data=bytes_data, mimetype=mime_type)
                                task["source_key"] = key
                                break  # 每个 task 只会有一种媒体类型

        return data_to_write

    def _read_file(self, path: str) -> dict[str, Any]:
        """Read JSON file."""

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = cast(dict[str, Any], json.load(f))
                current_task = data.get("current_task", [])

                if current_task:
                    loop = self._ensure_loop()
                    future = asyncio.run_coroutine_threadsafe(
                        self.overload_binary_messages(current_task),
                        loop
                    )
                    future.result()

                return data
        except json.JSONDecodeError as e:
            raise SessionException(f"Invalid JSON in file {path}: {str(e)}") from e

    def _write_file(self, path: str, data: dict[str, Any]) -> None:
        """Write JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # This automic write ensure the completeness of session files in both single agent/ multi agents
        tmp = f"{path}.tmp"

        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(
            self.update_binary_data(data),
            loop
        )
        result = future.result()

        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)


def create_session_manager(graph_id: str, session_id: str):
    session_manager = settings.session_manager
    match session_manager.manager:
        case SessionManagerType.LOCAL | _:
            base_dir = session_manager.file.root
            folder = session_manager.file.folder
            storage_dir = os.path.join(base_dir, folder)
            return BinarySafeFileSessionManager(
                graph_id=graph_id, session_id=session_id, storage_dir=storage_dir  # type: ignore
            )
