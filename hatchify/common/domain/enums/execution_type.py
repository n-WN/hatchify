from enum import Enum


class ExecutionType(str, Enum):
    """执行类型 - 对应不同的任务场景"""
    WEBHOOK = "webhook"                      # Webhook 执行 (web_hook_router)
    GRAPH_BUILDER = "graph_builder"          # Graph 对话 (graph_router)
    WEB_BUILDER = "web_builder"              # Web Builder 对话 (web_builder_router)
    DEPLOY = "deploy"                        # 部署任务 (web_builder_router deploy)