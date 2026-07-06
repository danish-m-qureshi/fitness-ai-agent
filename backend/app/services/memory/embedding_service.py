import logging

import httpx
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed_text(self, text: str) -> list[float]:
        normalized_text = text.strip()
        if not normalized_text:
            raise AppException(
                message="Memory content must not be empty.",
                status_code=422,
                error_code="empty_memory_content",
            )

        return self._embed_with_ollama(normalized_text)

    def _embed_with_ollama(self, text: str) -> list[float]:
        endpoint_payloads = [
            ("/api/embed", {"model": self.model, "input": text}),
            ("/api/embeddings", {"model": self.model, "prompt": text}),
        ]
        not_found_messages: list[str] = []

        for endpoint, payload in endpoint_payloads:
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        f"{self.base_url}{endpoint}",
                        json=payload,
                    )
                    response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    not_found_messages.append(exc.response.text)
                    continue

                logger.warning("Ollama embedding request failed: %s", exc)
                raise AppException(
                    message="Ollama embedding request failed.",
                    status_code=503,
                    error_code="ollama_embedding_failed",
                ) from exc
            except httpx.HTTPError as exc:
                logger.warning("Ollama embedding server unavailable: %s", exc)
                raise AppException(
                    message="Ollama embedding server is not reachable.",
                    status_code=503,
                    error_code="ollama_embedding_unavailable",
                ) from exc

            embedding = self._extract_embedding(response.json())
            if embedding:
                return embedding

        logger.warning(
            "Embedding model or API missing for model=%s details=%s",
            self.model,
            not_found_messages,
        )
        raise AppException(
            message=(
                f"Embedding model '{self.model}' is missing or Ollama "
                "embedding API is unavailable."
            ),
            status_code=503,
            error_code="embedding_model_missing",
        )

    def _extract_embedding(self, payload: dict) -> list[float]:
        embedding = payload.get("embedding")
        if isinstance(embedding, list):
            return [float(value) for value in embedding]

        embeddings = payload.get("embeddings")
        if (
            isinstance(embeddings, list)
            and embeddings
            and isinstance(embeddings[0], list)
        ):
            return [float(value) for value in embeddings[0]]

        raise AppException(
            message="Ollama returned an invalid embedding response.",
            status_code=503,
            error_code="invalid_embedding_response",
        )
