"""Webhook Router - 使用内存映射表模拟数据库

临时实现，用于测试GraphSpec执行流程
纯异步IO实现
"""
import json
import os.path
from typing import Dict, Any

import aiofiles
from fastapi import APIRouter, Request, HTTPException, UploadFile
from loguru import logger
from starlette.datastructures import FormData

from app.common.constants.constants import Constants
from app.common.domain.entity.graph_spec import GraphSpec
from app.common.domain.enums.storage_type import StorageType
from app.common.domain.result.result import Result
from app.common.extensions.ext_storage import storage_client
from app.core.builder.dynamic_graph_builder import DynamicGraphBuilder
from app.core.builder.graph_executor import GraphExecutor, GraphExecuteData, FileData
from app.core.hooks.graph_state_hook import GraphStateHook
from app.core.manager.function_manager import function_router
from app.core.manager.tool_manager import tool_factory
from app.core.utils.webhook_utils import infer_webhook_spec_from_schema

webhook_router = APIRouter(prefix="/webhooks")

# ============================================================
# 内存映射表 - 模拟数据库
# ============================================================
GRAPH_REGISTRY: Dict[str, GraphSpec] = {}


async def load_graph_from_json(json_path: str) -> GraphSpec:
    """从JSON文件异步加载GraphSpec"""
    async with aiofiles.open(json_path, "r", encoding="utf-8") as f:
        content = await f.read()
        data = json.loads(content)
    return GraphSpec(**data)


async def register_graph(graph_name: str, json_path: str):
    """异步注册Graph到内存映射表"""
    graph_spec = await load_graph_from_json(json_path)
    GRAPH_REGISTRY[graph_name] = graph_spec
    logger.info(f"✅ 已注册 Graph: {graph_name} (入口点: {graph_spec.entry_point})")


# ============================================================
# 启动时自动注册（模拟数据库初始化）
# ============================================================
async def init_graph_registry():
    """异步初始化Graph注册表"""
    await register_graph("gid_1", os.path.join(Constants.Path.GRAPH_JSONS, "pdf_analysis_system.json"))


async def prepare_data(graph_id: str, graph_spec: GraphSpec, request: Request, ):
    files: Dict[str, list[FileData]] = {}
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
                    source=StorageType.LOCAL
                )]
        for field_name in webhook_spec.data_fields:
            if field_name in form:
                json_data[field_name] = form[field_name]

    else:
        json_data = await request.json()

    execute_data = GraphExecuteData(jsons=json_data, files=files)
    return execute_data


# ============================================================
# Webhook处理器
# ============================================================
@webhook_router.post("/{graph_id}")
async def execute_graph_webhook(
        graph_id: str,
        request: Request,
) -> Result:
    graph_spec = GRAPH_REGISTRY.get(graph_id)
    if not graph_spec:
        return Result.failed(code=404, message="Graph '{graph_id}' not found")

    execute_data = await prepare_data(graph_id, graph_spec, request)

    builder = DynamicGraphBuilder(
        tool_router=tool_factory,
        function_router=function_router,
        hooks=[GraphStateHook()]
    )

    graph = builder.build_graph(graph_spec)

    executor = GraphExecutor(graph)

    try:
        result = await executor.invoke_async(execute_data)
        return Result.ok(data=result.results)

    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(msg)
        return Result.failed(message=msg)


@webhook_router.get("/{graph_id}/webhook-info")
async def get_webhook_info(graph_id: str):
    """查看Graph的Webhook配置信息"""
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
    }
