from textwrap import dedent

from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse

from hatchify.common.constants.constants import Constants
from hatchify.core.stream_handler.deploy import MOUNTED_GRAPHS
from hatchify.core.utils.quick_init_utils import get_repository_path


class PreviewMiddleware(BaseHTTPMiddleware):
    """预览路由中间件 - 按需挂载静态文件"""

    async def dispatch(self, request: Request, call_next):
        # 检查是否是预览请求
        if request.url.path.startswith(Constants.WebBuilder.PREVIEW_PREFIX + "/"):
            # 提取 graph_id
            path_parts = request.url.path[len(Constants.WebBuilder.PREVIEW_PREFIX) + 1:].split('/', 1)
            graph_id_clean = path_parts[0]
            target_path = f"{Constants.WebBuilder.PREVIEW_PREFIX}/{graph_id_clean}"

            # 检查是否已挂载
            if graph_id_clean not in MOUNTED_GRAPHS:
                # 未挂载,检查 dist/ 是否存在
                project_path = get_repository_path(graph_id_clean)
                dist_path = project_path / Constants.WebBuilder.DIST_DIR

                if not dist_path.exists():
                    return HTMLResponse(
                        content=dedent("""<!DOCTYPE html>
                            <html lang="zh">
                            <head>
                                <meta charset="UTF-8">
                                <title>Hatchify</title>
                            </head>
                            <body>
                            <div></div>
                            </body>
                            </html>"""
                    ),
                        status_code=200
                    )

                # 动态挂载
                logger.info(f"按需挂载: {target_path} -> {dist_path}")
                static_app = StaticFiles(directory=str(dist_path), html=True)
                request.app.mount(target_path, static_app, name=f"preview_{graph_id_clean}")
                MOUNTED_GRAPHS[graph_id_clean] = str(dist_path)

        # 继续处理请求
        response = await call_next(request)
        return response
