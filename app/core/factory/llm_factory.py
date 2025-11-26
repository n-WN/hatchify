from typing import Dict, Any

from strands.models import Model
from strands.models.gemini import GeminiModel
from strands.models.litellm import LiteLLMModel
from strands.models.openai import OpenAIModel

from app.common.domain.entity.agent_card import AgentCard
from app.common.domain.entity.model_card import ModelCard, ProviderCard
from app.core.manager.model_card_manager import model_card_manager


def get_model_by_family(
        provider_card: ProviderCard,
        model_card: ModelCard,
        client_args: Dict[str, Any],
        max_tokens: int
) -> Model:
    match provider_card.family:
        case "openai":
            params = {
                "max_completion_tokens": max_tokens,
            }
            return OpenAIModel(
                client_args=client_args,
                model_id=model_card.id,
                params=params
            )
        case "gemini":
            params = {
                "max_output_tokens": max_tokens,
            }
            return GeminiModel(
                client_args=client_args,
                model_id=model_card.id,
                params=params
            )
        case _:
            # 其他 provider 使用 LiteLLMModel
            params = {
                "max_completion_tokens": max_tokens,
            }
            return LiteLLMModel(
                client_args=client_args,
                model_id=f"{provider_card.family}/{model_card.id}",
                params=params
            )


def create_llm_by_model_card(model_card: ModelCard) -> Model:
    provider_card = model_card_manager.get_active_provider(model_card.provider_id)

    base_url = provider_card.base_url
    api_key = provider_card.api_key
    client_args = {}
    if api_key is not None:
        client_args["api_key"] = api_key
    if base_url is not None:
        client_args["base_url"] = base_url

    return get_model_by_family(provider_card, model_card, client_args, provider_card.max_tokens)


def create_llm_by_agent_card(agent_card: AgentCard) -> Model:
    """
    创建 LLM 实例，支持灵活的参数覆盖策略。

    覆盖优先级: agent 配置 > provider 配置 > None (由 LiteLLM 处理)

    注意: 如果 base_url 为 None，则必须提供 api_key（标准云服务）
          如果有 base_url，则 api_key 可以为 None（本地服务、私有服务）

    +------------------+---------------------+---------------------+---------------------------------------+
    | 场景             | Agent               | Provider            | 最终结果                              |
    +------------------+---------------------+---------------------+---------------------------------------+
    | 完全覆盖         | base_url + api_key  | base_url + api_key  | 使用 agent 的配置                     |
    | 部分覆盖 base_url | base_url            | api_key             | agent.base_url + provider.api_key    |
    | 部分覆盖 api_key  | api_key             | base_url            | provider.base_url + agent.api_key    |
    | 标准云服务       | -                   | api_key (无 base_url)| 只传 api_key，由 LiteLLM 处理 URL    |
    | Ollama 本地      | -                   | base_url (无 api_key)| 只传 base_url                        |
    | 私有服务         | base_url (无 api_key)| -                   | 只传 agent.base_url                  |
    +------------------+---------------------+---------------------+---------------------------------------+
    """
    # 使用 fallback 机制：优先在指定 provider 查找，找不到则按优先级在其他 enabled providers 中查找
    model_card = model_card_manager.find_model_with_fallback(agent_card.model, agent_card.provider)
    provider_card = model_card_manager.get_active_provider(model_card.provider_id)

    # 灵活的参数覆盖逻辑：agent 优先，否则使用 provider，都没有则为 None
    # agent.base_url 优先于 provider.base_url
    base_url = agent_card.base_url if agent_card.base_url is not None else provider_card.base_url

    # agent.api_key 优先于 provider.api_key
    api_key = agent_card.api_key if agent_card.api_key is not None else provider_card.api_key

    # 验证配置有效性：如果没有 base_url，则必须有 api_key
    if base_url is None and api_key is None:
        raise ValueError(
            f"Invalid LLM configuration for agent '{agent_card.name}': "
            f"Either base_url or api_key must be provided. "
            f"For standard cloud services (OpenAI, Anthropic, etc.), provide api_key. "
            f"For local/private services (Ollama, etc.), provide base_url."
        )

    # max_tokens 覆盖逻辑
    max_tokens = agent_card.max_tokens or model_card.max_tokens

    # 构建 client_args，只包含非 None 的参数
    client_args = {}
    if api_key is not None:
        client_args["api_key"] = api_key
    if base_url is not None:
        client_args["base_url"] = base_url

    return get_model_by_family(provider_card, model_card, client_args, max_tokens)
