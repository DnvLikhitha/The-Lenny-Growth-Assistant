import os
import json
from typing import AsyncIterator, List, Dict, Any, Optional
import httpx
from backend.providers.base import ModelProvider, ProviderError

class OllamaProvider(ModelProvider):
    def __init__(self, model_name: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 300.0):
        self.model_name = model_name or os.getenv("LLM_MODEL", "llama3.1:8b")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"ollama/{self.model_name}"

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    # Check if model exists or prefix matches
                    return any(self.model_name in m or m in self.model_name for m in models) or len(models) > 0
                return False
        except Exception:
            return False

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        stream: bool = True
    ) -> AsyncIterator[str]:
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for msg in messages:
            ollama_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": stream,
            "options": {"num_predict": max_tokens}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            raise ProviderError(
                                message=f"Ollama returned HTTP status {response.status_code}",
                                code="OLLAMA_HTTP_ERROR",
                                detail=error_body.decode("utf-8", errors="ignore")
                            )
                        async for line in response.aiter_lines():
                            if line:
                                data = json.loads(line)
                                delta = data.get("message", {}).get("content", "")
                                if delta:
                                    yield delta
                else:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    if response.status_code != 200:
                        raise ProviderError(
                            message=f"Ollama returned HTTP status {response.status_code}",
                            code="OLLAMA_HTTP_ERROR",
                            detail=response.text
                        )
                    data = response.json()
                    yield data.get("message", {}).get("content", "")
        except httpx.ConnectError:
            raise ProviderError(
                message=f"Ollama host is unreachable at {self.base_url}. Please ensure Ollama is running.",
                code="OLLAMA_UNREACHABLE"
            )
        except httpx.TimeoutException:
            raise ProviderError(
                message=f"Ollama request timed out after {self.timeout}s.",
                code="OLLAMA_TIMEOUT"
            )
        except Exception as e:
            if isinstance(e, ProviderError):
                raise e
            raise ProviderError(message=f"Unexpected Ollama error: {str(e)}", code="OLLAMA_ERROR")
