from typing import List, Dict, Any, Union

from loguru import logger
from pydantic import BaseModel
from strands.tools.decorator import DecoratedFunctionTool

from hatchify.common.domain.entity.agent_node_spec import AgentNode
from hatchify.common.domain.entity.function_node_spec import FunctionNode
from hatchify.common.domain.entity.graph_spec import GraphSpec
from hatchify.core.factory.tool_factory import ToolRouter


def find_terminal_nodes(graph_spec: GraphSpec) -> List[str]:
    """找到终端节点（没有出边的节点）

    使用集合运算：all_nodes - source_nodes

    Args:
        graph_spec: Graph 规范对象

    Returns:
        终端节点名称列表
    """
    # 所有节点
    all_nodes = set(graph_spec.nodes)

    # 所有作为起始节点的节点（有出边）
    source_nodes = {edge.from_node for edge in graph_spec.edges}

    # 终端节点 = 所有节点 - 有出边的节点
    terminal_nodes = all_nodes - source_nodes

    logger.debug(
        f"找到 {len(terminal_nodes)} 个终端节点: {terminal_nodes} "
        f"(总节点数: {len(all_nodes)})"
    )

    return list(terminal_nodes)


def generate_output_schema(
        graph_spec: GraphSpec,
        function_router: ToolRouter[DecoratedFunctionTool]
) -> Dict[str, Any]:
    """从终端节点自动生成 Graph 的 output_schema

    提取逻辑：
    1. 找到所有终端节点
    2. 对于每个终端节点：
       - AgentNode: 读取 structured_output_schema
       - FunctionNode: 从 function_router 获取工具的输出 schema
    3. 合并所有 schema 为一个 properties 对象

    Args:
        graph_spec: Graph 规范对象
        function_router: Function 工具路由器（用于获取 FunctionNode 的输出 schema）

    Returns:
        JSON Schema dict，格式为：
        {
            "type": "object",
            "properties": {
                "node1_output": {...},
                "node2_output": {...}
            },
            "required": ["node1_output", "node2_output"]
        }
    """
    # Step 1: 找到终端节点
    terminal_node_names = find_terminal_nodes(graph_spec)

    if not terminal_node_names:
        logger.warning("Graph 没有终端节点，无法生成 output_schema")
        raise RuntimeError("Not found terminal nodes")

    # Step 2: 构建 node_name -> node 的映射
    node_map: Dict[str, Union[AgentNode, FunctionNode]] = {}

    for agent in graph_spec.agents:
        node_map[agent.name] = agent

    for function in graph_spec.functions:
        node_map[function.name] = function

    # Step 3: 提取每个终端节点的 schema
    properties = {}
    required = []

    for node_name in terminal_node_names:
        if node_name not in node_map:
            logger.warning(f"终端节点 '{node_name}' 不存在于 Graph 定义中，跳过")
            continue

        node = node_map[node_name]
        node_schema = None

        if isinstance(node, AgentNode):
            # AgentNode: 直接读取 structured_output_schema
            node_schema = node.structured_output_schema

            if node_schema:
                logger.debug(
                    f"提取 Agent 节点 '{node_name}' 的 output schema: "
                    f"{node_schema.get('type', 'unknown')}"
                )
            else:
                logger.warning(
                    f"Agent 节点 '{node_name}' 没有 structured_output_schema，"
                    f"将使用通用 string 类型"
                )
                # 没有 schema 的 Agent，假设输出为字符串
                node_schema = {
                    "type": "string",
                    "description": f"Output from agent {node_name}"
                }

        elif isinstance(node, FunctionNode):
            # FunctionNode: 从 function_router 获取工具定义
            try:
                tool: DecoratedFunctionTool = function_router.get_tool(node.function_ref)
                base_model: BaseModel = function_router.get_function_output_model(tool)
                node_schema = base_model.model_json_schema()
            except KeyError:
                logger.error(
                    f"Function 节点 '{node_name}' 引用的工具 '{node.function_ref}' 不存在"
                )
                # 使用占位符 schema
                node_schema = {
                    "type": "object",
                    "description": f"Output from missing function {node.function_ref}"
                }

        # 添加到 properties
        if node_schema:
            properties[node_name] = node_schema
            required.append(node_name)

    # Step 4: 构建最终的 output_schema
    output_schema = {
        "type": "object",
        "properties": properties,
        "required": required,
        "description": f"Workflow output from {len(terminal_node_names)} terminal node(s)"
    }

    logger.info(
        f"生成 output_schema 完成: {len(properties)} 个输出字段 "
        f"(来自 {len(terminal_node_names)} 个终端节点)"
    )

    return output_schema
