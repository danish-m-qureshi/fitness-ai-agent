import logging
from typing import Any

import httpx
from app.services.llm.base import VisionLLMClient, VisionLLMError

logger = logging.getLogger(__name__)


class OllamaVisionClient(VisionLLMClient):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def analyze_image(self, image_base64: str, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama image analysis request failed: %s", exc)
            error_detail = self._error_detail(exc.response)
            if exc.response.status_code == 404:
                raise VisionLLMError(
                    "Configured vision model is missing or not ready."
                ) from exc

            raise VisionLLMError(
                f"Ollama image analysis request failed: {error_detail}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("Ollama image analysis request failed: %s", exc)
            raise VisionLLMError("Ollama image analysis request failed.") from exc

        data = response.json()
        raw_response = data.get("response") or data.get("thinking") or ""

        return {
            "model": self.model,
            "raw_response": raw_response,
            "done": data.get("done", False),
        }

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.info("Ollama health check failed: %s", exc)
            return {
                "provider": "ollama",
                "base_url": self.base_url,
                "model": self.model,
                "server_reachable": False,
                "model_available": False,
                "available_models": [],
                "status": "unavailable",
                "error": "Ollama server is not reachable.",
            }

        data = response.json()
        available_models = [
            model.get("name", "")
            for model in data.get("models", [])
            if model.get("name")
        ]
        model_available = self.model in available_models

        return {
            "provider": "ollama",
            "base_url": self.base_url,
            "model": self.model,
            "server_reachable": True,
            "model_available": model_available,
            "available_models": available_models,
            "status": "ok" if model_available else "model_missing",
            "error": None if model_available else "Configured vision model is missing.",
        }

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or response.reason_phrase

        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()

        return response.reason_phrase
