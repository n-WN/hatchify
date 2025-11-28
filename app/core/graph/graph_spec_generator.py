import json
from typing import List, Dict, Any, Union, Tuple, Optional

from litellm.types.completion import ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam, ChatCompletionMessageParam
from litellm.types.utils import Usage
from loguru import logger
from strands.tools.decorator import DecoratedFunctionTool

from app.common.domain.entity.agent_node_spec import AgentNode
from app.common.domain.entity.function_node_spec import FunctionNode
from app.common.domain.entity.graph_spec import GraphSpec, Edge
from app.common.domain.structured_output.graph_generation_output import AgentSchema
from app.common.domain.structured_output.graph_generation_output import (
    GraphArchitectureOutput,
    SchemaExtractionOutput,
)
from app.common.domain.structured_output.pre_defined_schema import get_predefined_schema
from app.common.settings.settings import get_hatchify_settings
from app.core.factory.tool_factory import ToolRouter
from app.core.manager.model_card_manager import ModelCardManager
from app.core.prompts.prompts import (
    GRAPH_GENERATOR_SYSTEM_PROMPT,
    GRAPH_GENERATOR_USER_PROMPT,
    GRAPH_REFINEMENT_SYSTEM_PROMPT,
    GRAPH_REFINEMENT_USER_PROMPT,
    SCHEMA_EXTRACTOR_PROMPT, RESOURCE_MESSAGE,
)
from app.core.utils.json_generator import json_generator
from app.core.utils.schema_utils import generate_output_schema


class GraphSpecGenerator:
    """使用 LLM 生成 GraphSpec

    基于自然语言描述，通过两步 LLM 调用生成完整的 GraphSpec：
    1. 生成 Graph 架构（agents, functions, edges）
    2. 从 agent instructions 中提取 JSON schemas

    Example:
        ```python
        from app.core.manager.tool_manager import tool_factory
        from app.core.manager.function_manager import function_router

        generator = GraphSpecGenerator(
            tool_router=tool_factory,
            function_router=function_router
        )

        graph_spec = await generator.generate_graph_spec(
            user_description="创建一个成语接龙的 graph，4个 agent 依次接龙"
        )
        ```
    """

    def __init__(
            self,
            model_card_manager: ModelCardManager,
            tool_router: ToolRouter,
            function_router: ToolRouter[DecoratedFunctionTool],
    ):
        """初始化 GraphSpecGenerator

        Args:
            tool_router: Agent 工具路由器（来自 tool_manager）
            function_router: Function 路由器（来自 function_manager）

        注意：模型配置从 settings.yaml 读取
        """
        self.model_card_manager = model_card_manager
        self.tool_router = tool_router
        self.function_router = function_router

        # 从配置读取模型设置
        settings = get_hatchify_settings()
        if not settings or not settings.models:
            raise ValueError("配置文件中未找到 models 配置")

        self.spec_gen_config = settings.models.spec_generator
        self.spec_ext_config = settings.models.spec_generator

    async def generate_graph_spec(
            self,
            pre_graph_spec: Dict[str, Any],
            user_messages: List[Dict[str, Any]],
            history_messages: List[Dict[str, Any]]
    ) -> GraphSpec:
        logger.info("开始生成 GraphSpec")

        # Step 1: 调用 LLM 生成 Graph 架构
        graph_arch, usage = await self._generate_graph_architecture(
            pre_graph_spec=pre_graph_spec,
            user_messages=user_messages,
            history_messages=history_messages
        )

        logger.info(f"Step 1 完成: 生成了 {len(graph_arch.agents)} 个 agents, "
                    f"{len(graph_arch.functions)} 个 functions")

        # Step 2: 调用 LLM 提取 JSON schemas
        schemas_output, usages = await self._extract_schemas(graph_arch)

        logger.info(f"Step 2 完成: 提取了 {len(schemas_output.agent_schemas)} 个 schemas")

        # Step 3: 合并 schemas 并创建 GraphSpec
        graph_spec = self._merge_and_create_spec(graph_arch, schemas_output)

        logger.info(f"GraphSpec 生成完成: {graph_spec.name}")

        return graph_spec

    async def _generate_graph_architecture(
            self,
            pre_graph_spec: Dict[str, Any],
            user_messages: List[Dict[str, Any]],
            history_messages: List[Dict[str, Any]]
    ) -> Tuple[GraphArchitectureOutput, Optional[Usage]]:
        """Step 1: 生成 Graph 架构

        使用 structured_output 调用 LLM，返回类型安全的 GraphArchitectureOutput
        """
        resource_message = RESOURCE_MESSAGE.format(
            available_models=self.model_card_manager.format_models_for_prompt(),
            available_tools=self.tool_router.format_for_prompt(),
            available_functions=self.function_router.format_functions_for_prompt(),
        )
        messages: List[Union[ChatCompletionMessageParam, Dict[str, Any]]] = [
            ChatCompletionSystemMessageParam(
                role="system",
                content=GRAPH_GENERATOR_SYSTEM_PROMPT
            ),
            ChatCompletionSystemMessageParam(
                role="system",
                content=resource_message
            ),
        ]
        if pre_graph_spec:
            messages.append(
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=GRAPH_REFINEMENT_SYSTEM_PROMPT
                )
            )
        messages.extend(history_messages)
        messages.append(
            ChatCompletionUserMessageParam(
                role="user",
                content=GRAPH_GENERATOR_USER_PROMPT
            )
        )
        if pre_graph_spec:
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content=GRAPH_REFINEMENT_USER_PROMPT.format(
                        current_graph_spec=json.dumps(
                            pre_graph_spec,
                            ensure_ascii=False,
                            indent=2
                        )
                    )
                )
            )
        messages.extend(user_messages)
        result, usage = await json_generator(
            provider_id=self.spec_gen_config.provider,
            model_id=self.spec_gen_config.model,
            messages=messages,
            response_model=GraphArchitectureOutput,
            max_retries=3,
        )

        return result, usage

    async def _extract_schemas(
            self,
            graph_arch: GraphArchitectureOutput,
    ) -> Tuple[SchemaExtractionOutput, List[Usage]]:
        """Step 2: 从 agent instructions 提取 JSON schemas

        Router/Orchestrator 使用预定义 schema，General Agent 通过 LLM 提取。
        """
        usages = []
        agent_schemas = []

        # 分离需要预定义 schema 的 agent 和需要 LLM 提取的 agent
        agents_needing_llm = []

        for agent in graph_arch.agents:
            # 尝试获取预定义 schema
            predefined_schema = get_predefined_schema(agent.category)

            if predefined_schema:
                # 使用预定义 schema
                agent_schemas.append(
                    AgentSchema(
                        agent_name=agent.name,
                        structured_output_schema=predefined_schema
                    )
                )
                logger.info(
                    f"Using predefined schema for {agent.category} agent: {agent.name}"
                )
            else:
                # 需要 LLM 提取
                agents_needing_llm.append(agent)

        # 如果有需要 LLM 提取的 agent，调用 LLM
        if agents_needing_llm:
            # 构建只包含需要提取的 agent 的临时架构
            temp_arch = GraphArchitectureOutput(
                name=graph_arch.name,
                description=graph_arch.description,
                agents=agents_needing_llm,
                functions=graph_arch.functions,
                nodes=graph_arch.nodes,
                edges=graph_arch.edges,
                entry_point=graph_arch.entry_point
            )

            # 构建 user prompt
            user_prompt = SCHEMA_EXTRACTOR_PROMPT.format(
                graph_spec=temp_arch.model_dump_json(indent=2, ensure_ascii=False)
            )

            logger.info(
                f"Calling Schema Extractor LLM for {len(agents_needing_llm)} general agents..."
            )

            # 使用 json_generator - 自动处理 JSON 解析、验证和重试
            llm_result, usage = await json_generator(
                provider_id=self.spec_ext_config.provider,
                model_id=self.spec_ext_config.model,
                messages=[
                    ChatCompletionSystemMessageParam(
                        role="system",
                        content="You are a JSON schema expert. Extract schemas accurately from agent instructions."
                    ),
                    ChatCompletionUserMessageParam(
                        role="user",
                        content=user_prompt
                    )
                ],
                response_model=SchemaExtractionOutput,
                max_retries=3,
            )

            # 合并 LLM 提取的 schemas
            usages.append(usage)
            agent_schemas.extend(llm_result.agent_schemas)

        # 返回完整的 SchemaExtractionOutput
        return SchemaExtractionOutput(agent_schemas=agent_schemas), usages

    def _merge_and_create_spec(
            self,
            graph_arch: GraphArchitectureOutput,
            schemas_output: SchemaExtractionOutput,
    ) -> GraphSpec:
        """Step 3: 合并 schemas 并创建 GraphSpec 对象

        将 LLM 返回的 Pydantic 对象转换为 GraphSpec，
        并自动生成 output_schema（从终端节点提取）。
        """
        # 创建 agent name -> schema 的映射
        schema_map = {
            schema.agent_name: schema.structured_output_schema
            for schema in schemas_output.agent_schemas
        }

        # 解析 agents
        agents = []
        for agent_arch in graph_arch.agents:
            # 从映射中获取对应的 schema
            structured_output_schema = schema_map.get(agent_arch.name)

            # 创建 AgentNode
            agent_node = AgentNode(
                name=agent_arch.name,
                model=agent_arch.model,
                instruction=agent_arch.instruction,
                category=agent_arch.category,
                tools=agent_arch.tools,
                structured_output_schema=structured_output_schema,
            )
            agents.append(agent_node)

        # 解析 functions
        functions = []
        for func_arch in graph_arch.functions:
            function_node = FunctionNode(
                name=func_arch.name,
                function_ref=func_arch.function_ref,
            )
            functions.append(function_node)

        # 解析 edges
        edges = []
        for edge_arch in graph_arch.edges:
            edge = Edge(
                from_node=edge_arch.from_node,
                to_node=edge_arch.to_node,
            )
            edges.append(edge)

        # 创建 GraphSpec（先创建用于后续生成 output_schema）
        graph_spec = GraphSpec(
            name=graph_arch.name,
            description=graph_arch.description,
            agents=agents,
            functions=functions,
            nodes=graph_arch.nodes,
            edges=edges,
            entry_point=graph_arch.entry_point,
            input_schema=graph_arch.input_schema,  # 从 LLM 生成的架构中获取
            output_schema=None,
        )

        # Step 4: 自动生成 output_schema（从终端节点提取）
        try:
            output_schema = generate_output_schema(graph_spec, self.function_router)
            graph_spec.output_schema = output_schema
            logger.info(
                f"自动生成 output_schema: {len(output_schema.get('properties', {}))} 个输出字段"
            )
        except Exception as e:
            logger.error(f"生成 output_schema 失败: {e}", exc_info=True)

        return graph_spec
