from abc import ABC, abstractmethod
from typing import Any


class VisionLLMError(Exception):
    pass


class VisionLLMClient(ABC):
    @abstractmethod
    async def analyze_image(self, image_base64: str, prompt: str) -> dict[str, Any]:
        pass

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        pass
