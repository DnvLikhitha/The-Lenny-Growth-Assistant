import os
from typing import AsyncIterator, List, Dict, Any, Optional
import anthropic
from backend.providers.base import ModelProvider, ProviderError

class AnthropicProvider(ModelProvider):
    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.model_name = model_name or os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    @property
    def name(self) -> str:
        return f"anthropic/{self.model_name}"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        stream: bool = True
    ) -> AsyncIterator[str]:
        if not self.is_available():
            raise ProviderError(
                message="Anthropic API key is missing or not configured in environment.",
                code="ANTHROPIC_KEY_MISSING"
            )

        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        formatted_messages = []
        for msg in messages:
            role = msg["role"]
            if role not in ("user", "assistant"):
                role = "user"
            formatted_messages.append({"role": role, "content": msg["content"]})

        kwargs = {
            "model": self.model_name,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system

        try:
            if stream:
                async with client.messages.stream(**kwargs) as stream_ctx:
                    async for text in stream_ctx.text_stream:
                        yield text
            else:
                response = await client.messages.create(**kwargs)
                for block in response.content:
                    if block.type == "text":
                        yield block.text
        except anthropic.AuthenticationError:
            raise ProviderError(
                message="Invalid Anthropic API key provided.",
                code="ANTHROPIC_AUTH_FAILED"
            )
        except anthropic.APIError as e:
            raise ProviderError(
                message=f"Anthropic API error: {e.message}",
                code="ANTHROPIC_API_ERROR",
                detail=str(e)
            )
        except Exception as e:
            raise ProviderError(
                message=f"Unexpected Anthropic provider error: {str(e)}",
                code="ANTHROPIC_ERROR"
            )
