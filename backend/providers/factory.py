import os
from typing import Optional
from backend.providers.base import ModelProvider, ProviderError
from backend.providers.ollama import OllamaProvider
from backend.providers.anthropic_provider import AnthropicProvider

def get_model_provider(
    provider_type: Optional[str] = None,
    model_name: Optional[str] = None
) -> ModelProvider:
    provider_str = (provider_type or os.getenv("LLM_PROVIDER", "ollama")).lower().strip()
    
    if provider_str == "ollama":
        return OllamaProvider(model_name=model_name)
    elif provider_str in ("anthropic", "claude"):
        return AnthropicProvider(model_name=model_name)
    else:
        raise ProviderError(
            message=f"Unsupported or unknown LLM_PROVIDER '{provider_str}'. Must be 'ollama' or 'anthropic'.",
            code="INVALID_PROVIDER"
        )
