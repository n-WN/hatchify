import asyncio
import json
import os.path
import uuid
from typing import Dict, Any, Optional, List

import aiofiles
from fastapi import APIRouter, Request, HTTPException, UploadFile, Header, Query
from loguru import logger
from starlette.datastructures import FormData
from starlette.responses import StreamingResponse

from app.common.constants.constants import Constants
from app.common.domain.entity.graph_execute_data import FileData, GraphExecuteData
from app.common.domain.entity.graph_spec import GraphSpec
from app.common.domain.result.result import Result
from app.common.extensions.ext_storage import storage_client
from app.common.settings.settings import get_hatchify_settings
from app.core.factory.session_manager_factory import create_session_manager
from app.core.graph.dynamic_graph_builder import DynamicGraphBuilder
from app.core.manager.executor_manager import ExecutorManager
from app.core.graph.graph_executor import GraphExecutor
from app.core.hooks.graph_state_hook import GraphStateHook
from app.core.manager.function_manager import function_router
from app.core.manager.tool_manager import tool_factory
from app.core.utils.webhook_utils import infer_webhook_spec_from_schema

settings = get_hatchify_settings()
webhook_router = APIRouter(prefix="/webhooks")

GRAPH_REGISTRY: Dict[str, GraphSpec] = {}


async def load_graph_from_json(json_path: str) -> GraphSpec:
    async with aiofiles.open(json_path, "r", encoding="utf-8") as f:
        content = await f.read()
        data = json.loads(content)
    return GraphSpec(**data)


async def register_graph(graph_name: str, json_path: str):
    graph_spec = await load_graph_from_json(json_path)
    GRAPH_REGISTRY[graph_name] = graph_spec


async def init_graph_registry():
    await register_graph("gid_1", os.path.join(Constants.Path.GRAPH_JSONS, "pdf_analysis_system.json"))


async def prepare_data(graph_id: str, graph_spec: GraphSpec, request: Request):
    files: Dict[str, List[FileData]] = {}
    json_data: Dict[str, Any] = {}
    webhook_spec = infer_webhook_spec_from_schema(graph_spec.input_schema)
    if webhook_spec.input_type == "multipart/form-data":

        form: FormData = await request.form()

        for field_name in webhook_spec.file_fields:
            if field_name in form:
                uploaded_file: UploadFile = form[field_name]
                key = f"hatchify__{graph_id}__{field_name}__{uploaded_file.filename}"
                await storage_client.save(key=key, data=await uploaded_file.read(), mimetype=uploaded_file.content_type)
                files[field_name] = [FileData(
                    key=key,
                    mime=uploaded_file.content_type or "application/octet-stream",
                    name=uploaded_file.filename,
                    source=settings.storage.platform
                )]
        for field_name in webhook_spec.data_fields:
            if field_name in form:
                json_data[field_name] = form[field_name]

    else:
        json_data = await request.json()

    execute_data = GraphExecuteData(jsons=json_data, files=files)
    return execute_data


@webhook_router.post("/invoke/{graph_id}")
async def invoke_graph(
        graph_id: str,
        request: Request,
) -> Result[Dict[str, Any]]:
    result_dict = {}
    session_id = uuid.uuid4().hex
    graph_spec = GRAPH_REGISTRY.get(graph_id)
    if not graph_spec:
        return Result.failed(code=404, message=f"Graph '{graph_id}' not found")

    output_required = graph_spec.output_schema.get("required", [])
    execute_data = await prepare_data(graph_id, graph_spec, request)

    builder = DynamicGraphBuilder(
        tool_router=tool_factory,
        function_router=function_router,
        hooks=[GraphStateHook()],
        session_manager=create_session_manager(session_id=session_id)
    )

    graph = builder.build_graph(graph_spec)

    executor = GraphExecutor(graph_id, graph)

    try:
        graph_result = await executor.invoke_async(execute_data)

        for node, node_result in graph_result.results.items():
            if node in output_required:
                result_dict[node] = node_result.result.structured_output.model_dump()

        return Result.ok(data=result_dict)

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(msg)
        return Result.failed(message=msg)


@webhook_router.post("/execute/{graph_id}")
async def execute_graph_stream(
        graph_id: str,
        request: Request,
) -> Result[Dict[str, str]]:
    """
    启动图执行任务（双端点模式第一步）

    返回 execution_id 和 stream_url，客户端使用 stream_url 订阅事件流
    支持断线重连
    """
    graph_spec = GRAPH_REGISTRY.get(graph_id)
    if not graph_spec:
        return Result.failed(code=404, message=f"Graph '{graph_id}' not found")

    # 生成唯一的 execution_id
    execution_id = uuid.uuid4().hex

    try:
        # 准备数据
        execute_data = await prepare_data(graph_id, graph_spec, request)

        # 构建 graph
        builder = DynamicGraphBuilder(
            tool_router=tool_factory,
            function_router=function_router,
            hooks=[GraphStateHook()],
            session_manager=create_session_manager(session_id=execution_id)
        )
        graph = builder.build_graph(graph_spec)

        executor = GraphExecutor(
            execution_id,
            graph,
            enable_reconnect=True,
            ping_interval=15,
            event_ttl=900
        )

        await ExecutorManager.create(execution_id, executor)

        asyncio.create_task(executor.run_streamed(execute_data))

        logger.info(f"Started execution: {execution_id} for graph: {graph_id}")

        return Result.ok(
            data={
                "graph_id": graph_id,
                "execution_id": execution_id,
                "stream_url": f"/webhooks/stream/{execution_id}",

            })

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(msg)
        return Result.failed(message=msg)


@webhook_router.get("/stream/{execution_id}")
async def subscribe_stream(
        execution_id: str,
        last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
        latest_id: Optional[str] = Query(None)
):
    executor = await ExecutorManager.get(execution_id)
    if not executor:
        raise HTTPException(
            status_code=404,
            detail=f"Execution '{execution_id}' not found. It may have expired or been cleaned up."
        )

    effective_last_id = latest_id or last_event_id

    try:
        return StreamingResponse(
            executor.worker(last_event_id=effective_last_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(f"Stream error for execution {execution_id}: {msg}")
        raise HTTPException(status_code=500, detail=msg)


@webhook_router.get("/webhook-info/{graph_id}")
async def get_webhook_info(graph_id: str):
    graph_spec = GRAPH_REGISTRY.get(graph_id)
    if not graph_spec:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found")

    webhook_spec = infer_webhook_spec_from_schema(graph_spec.input_schema)

    return {
        "graph_id": graph_id,
        "input_type": webhook_spec.input_type,
        "file_fields": webhook_spec.file_fields,
        "data_fields": webhook_spec.data_fields,
        "input_schema": graph_spec.input_schema,
        "output_schema": graph_spec.output_schema,
    }
