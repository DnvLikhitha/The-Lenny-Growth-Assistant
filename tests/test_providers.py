import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from backend.providers.base import ProviderError
from backend.providers.ollama import OllamaProvider
from backend.providers.anthropic_provider import AnthropicProvider
from backend.providers.factory import get_model_provider

def test_factory_invalid_provider():
    with pytest.raises(ProviderError) as exc_info:
        get_model_provider(provider_type="invalid_provider")
    assert exc_info.value.code == "INVALID_PROVIDER"

def test_anthropic_missing_key():
    provider = AnthropicProvider(api_key="")
    assert provider.is_available() is False

@pytest.mark.asyncio
async def test_anthropic_generate_missing_key():
    provider = AnthropicProvider(api_key="")
    with pytest.raises(ProviderError) as exc_info:
        async for _ in provider.generate(messages=[{"role": "user", "content": "hi"}]):
            pass
    assert exc_info.value.code == "ANTHROPIC_KEY_MISSING"

@pytest.mark.asyncio
async def test_ollama_unreachable():
    provider = OllamaProvider(base_url="http://localhost:99999", timeout=0.1)
    with pytest.raises(ProviderError) as exc_info:
        async for _ in provider.generate(messages=[{"role": "user", "content": "hi"}]):
            pass
    assert exc_info.value.code in ("OLLAMA_UNREACHABLE", "OLLAMA_ERROR", "OLLAMA_TIMEOUT")

def test_ollama_is_available_mock():
    with patch("httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.get.return_value.status_code = 200
        mock_instance.get.return_value.json.return_value = {
            "models": [{"name": "llama3.1:8b"}]
        }
        mock_client.return_value.__enter__.return_value = mock_instance
        
        provider = OllamaProvider(model_name="llama3.1:8b")
        assert provider.is_available() is True
