from apps.config import ServerSettings
from apps.server.agent.messages import GenerationSettings
from apps.server.providers.base import LLMProvider


def create_provider(settings: ServerSettings) -> tuple[LLMProvider | None, str | None]:
    name = settings.llm_provider
    model = getattr(settings, name + "_model")
    if not model:
        return None, "provider_model_not_configured"
    if name == "ollama":
        from apps.server.providers.ollama import OllamaProvider

        return OllamaProvider(model, settings.ollama_base_url, settings.llm_timeout), None
    if not settings.allow_cloud:
        return None, "cloud_disabled"
    key = getattr(settings, name + "_api_key")
    if key is None or not key.get_secret_value().strip():
        return None, "provider_key_not_configured"
    if name == "openai":
        from apps.server.providers.openai import OpenAIProvider

        return OpenAIProvider(model, key.get_secret_value(), settings.llm_timeout), None
    from apps.server.providers.anthropic import AnthropicProvider

    return AnthropicProvider(model, key.get_secret_value(), settings.llm_timeout), None


def generation_settings(settings: ServerSettings) -> GenerationSettings:
    return GenerationSettings(
        max_output_tokens=settings.llm_max_output_tokens,
        temperature=settings.llm_temperature,
        think=settings.ollama_think if settings.llm_provider == "ollama" else None,
        reasoning_effort=(
            settings.openai_reasoning_effort if settings.llm_provider == "openai" else None
        ),
    )
