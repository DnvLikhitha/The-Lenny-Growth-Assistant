from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any, Optional

class ProviderError(Exception):
    def __init__(self, message: str, code: str = "PROVIDER_ERROR", detail: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.detail = detail

class ModelProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        stream: bool = True
    ) -> AsyncIterator[str]:
        pass
