import asyncio
import os
import shutil
from typing import AsyncIterator, Dict, Any

from fastapi.staticfiles import StaticFiles
from loguru import logger

from hatchify.common.domain.event.base_event import StreamEvent
from hatchify.common.domain.event.deploy_event import ProgressEvent, LogEvent, DeployResultEvent
from hatchify.core.stream_handler.stream_handler import BaseStreamHandler
from hatchify.common.constants.constants import Constants

# 全局状态：已挂载的项目
MOUNTED_GRAPHS: Dict[str, str] = {}  # {graph_id: dist_path}


class DeployGenerator(BaseStreamHandler):
    """部署流式处理器"""

    def __init__(
            self,
            source_id: str,
            graph_id: str,
            project_path: str,
            redeploy: bool = False,
    ):
        super().__init__(source_id=source_id, ping_interval=5)
        self.graph_id = graph_id
        self.project_path = project_path
        self.redeploy = redeploy

        # 预定义路径常量
        self.package_json_path = os.path.join(project_path, Constants.WebBuilder.PACKAGE_JSON)
        self.node_modules_path = os.path.join(project_path, Constants.WebBuilder.NODE_MODULES)
        self.dist_path = os.path.join(project_path, Constants.WebBuilder.DIST_DIR)
        self.preview_url = f"{Constants.WebBuilder.PREVIEW_PREFIX}/{graph_id}/"
        self.mount_path = f"{Constants.WebBuilder.PREVIEW_PREFIX}/{graph_id}"

    async def handle_stream_event(self, event: Any):
        await self.emit_event(event)

    @staticmethod
    async def _run_command_with_logs(
            cmd: list[str],
            cwd: str,
            stage: str
    ) -> AsyncIterator[StreamEvent]:
        """执行命令并实时推送日志"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # 实时读取输出
        if process.stdout:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                log_line = line.decode().rstrip()
                if log_line:
                    yield StreamEvent(
                        type="log",
                        data=LogEvent(content=f"[{stage}] {log_line}")
                    )

        await process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"{' '.join(cmd)} failed with code {process.returncode}")

    async def _check_and_mount_existing(self) -> AsyncIterator[StreamEvent]:
        """快速路径：检查并挂载已有的构建产物"""
        yield StreamEvent(
            type="progress",
            data=ProgressEvent(stage="checking", message="检测到已有构建产物")
        )
        yield StreamEvent(
            type="log",
            data=LogEvent(content=f"使用现有构建: {Constants.WebBuilder.DIST_DIR}/")
        )

        await self._mount_static_files()

        yield StreamEvent(
            type="deploy_result",
            data=DeployResultEvent(
                preview_url=self.preview_url,
                message=f"应用已部署到 {self.preview_url}"
            )
        )

    async def _clean_build_artifacts(self) -> AsyncIterator[StreamEvent]:
        """异步清理构建产物"""
        yield StreamEvent(
            type="progress",
            data=ProgressEvent(stage="checking", message="清理旧构建产物...")
        )

        # 使用 asyncio 异步删除
        tasks = []
        if os.path.exists(self.node_modules_path):
            tasks.append(asyncio.to_thread(shutil.rmtree, self.node_modules_path, False, None))  # type: ignore
            yield StreamEvent(
                type="log",
                data=LogEvent(content=f"正在删除 {Constants.WebBuilder.NODE_MODULES}/")
            )

        if os.path.exists(self.dist_path):
            tasks.append(asyncio.to_thread(shutil.rmtree, self.dist_path, False, None))  # type: ignore
            yield StreamEvent(
                type="log",
                data=LogEvent(content=f"正在删除 {Constants.WebBuilder.DIST_DIR}/")
            )

        if tasks:
            await asyncio.gather(*tasks)

        yield StreamEvent(
            type="progress",
            data=ProgressEvent(stage="checking", message="清理完成")
        )

    async def build_project(self) -> AsyncIterator[StreamEvent]:
        """构建项目的异步生成器"""
        # 检查项目
        if not os.path.exists(self.project_path):
            raise FileNotFoundError(f"项目目录不存在: {self.project_path}")
        if not os.path.exists(self.package_json_path):
            raise FileNotFoundError(f"{Constants.WebBuilder.PACKAGE_JSON} 不存在: {self.package_json_path}")

        # 快速路径：已有构建且不需要重建
        if not self.redeploy and os.path.exists(self.dist_path):
            async for event in self._check_and_mount_existing():
                yield event
            return

        # 需要重建：清理 -> 安装 -> 构建 -> 挂载
        if self.redeploy:
            async for event in self._clean_build_artifacts():
                yield event

        # 安装依赖
        if not os.path.exists(self.node_modules_path):
            yield StreamEvent(
                type="progress",
                data=ProgressEvent(stage="installing", message="安装依赖...")
            )
            async for event in self._run_command_with_logs(["npm", "install"], self.project_path, "npm install"):
                yield event

        # 构建
        yield StreamEvent(
            type="progress",
            data=ProgressEvent(stage="building", message="构建中...")
        )
        async for event in self._run_command_with_logs(["npm", "run", "build"], self.project_path, "npm run build"):
            yield event

        if not os.path.exists(self.dist_path):
            raise RuntimeError(f"构建完成但 {Constants.WebBuilder.DIST_DIR}/ 不存在")

        # 挂载
        await self._mount_static_files()

        yield StreamEvent(
            type="deploy_result",
            data=DeployResultEvent(
                preview_url=self.preview_url,
                message=f"应用已部署到 {self.preview_url}"
            )
        )

    async def _mount_static_files(self):
        from hatchify.launch.launch import app

        global MOUNTED_GRAPHS

        if self.graph_id in MOUNTED_GRAPHS:
            logger.info(f"Graph {self.graph_id} 已挂载，跳过")
            return

        try:
            app.mount(
                self.mount_path,
                StaticFiles(directory=self.dist_path, html=True),
                name=f"preview_{self.graph_id}"
            )

            MOUNTED_GRAPHS[self.graph_id] = self.dist_path
            logger.info(f"✅ 挂载成功: {self.mount_path} -> {self.dist_path}")

        except Exception as e:
            logger.error(f"挂载失败: {type(e).__name__}: {e}")
            raise

    async def submit_task(self):
        """提交部署任务"""
        async_generator = self.build_project()
        await self.run_streamed(async_generator)
