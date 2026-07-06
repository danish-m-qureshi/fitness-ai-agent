import logging
from typing import Any

import httpx
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = f"http://{host}:{port}".rstrip("/")
        self.collection_name = collection_name
        self.timeout_seconds = timeout_seconds

    def ensure_collection(self, vector_size: int) -> None:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(self._collection_url)

                if response.status_code == 200:
                    return

                if response.status_code != 404:
                    response.raise_for_status()

                create_response = client.put(
                    self._collection_url,
                    json={
                        "vectors": {
                            "size": vector_size,
                            "distance": "Cosine",
                        }
                    },
                )
                create_response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Qdrant collection check failed: %s", exc)
            raise AppException(
                message="Qdrant vector database is not reachable.",
                status_code=503,
                error_code="qdrant_unavailable",
            ) from exc

    def upsert_memory(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> str:
        self.ensure_collection(len(vector))

        body = {
            "points": [
                {
                    "id": memory_id,
                    "vector": vector,
                    "payload": payload,
                }
            ]
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.put(
                    f"{self._points_url}?wait=true",
                    json=body,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Qdrant memory upsert failed: %s", exc)
            raise AppException(
                message="Could not store memory in Qdrant.",
                status_code=503,
                error_code="memory_store_failed",
            ) from exc

        return memory_id

    def search_memory(
        self,
        vector: list[float],
        limit: int,
        user_id: int,
        memory_type: str | None = None,
    ) -> list[dict[str, Any]]:
        self.ensure_collection(len(vector))

        body: dict[str, Any] = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
            "filter": self._filter(user_id, memory_type),
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self._points_url}/search", json=body)

                if response.status_code == 404:
                    response = client.post(
                        f"{self._points_url}/query",
                        json={
                            "query": vector,
                            "limit": limit,
                            "with_payload": True,
                            "filter": self._filter(user_id, memory_type),
                        },
                    )

                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Qdrant memory search failed: %s", exc)
            raise AppException(
                message="Could not search memory in Qdrant.",
                status_code=503,
                error_code="memory_search_failed",
            ) from exc

        return self._extract_search_results(response.json())

    def delete_memory(self, memory_id: str) -> None:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self._points_url}/delete?wait=true",
                    json={"points": [memory_id]},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Qdrant memory delete failed: %s", exc)
            raise AppException(
                message="Could not delete memory from Qdrant.",
                status_code=503,
                error_code="memory_delete_failed",
            ) from exc

    @property
    def _collection_url(self) -> str:
        return f"{self.base_url}/collections/{self.collection_name}"

    @property
    def _points_url(self) -> str:
        return f"{self._collection_url}/points"

    def _filter(self, user_id: int, memory_type: str | None) -> dict[str, Any]:
        must_filters: list[dict[str, Any]] = [
            {"key": "user_id", "match": {"value": user_id}},
        ]

        if memory_type is not None:
            must_filters.append(
                {"key": "memory_type", "match": {"value": memory_type}},
            )

        return {"must": must_filters}

    def _extract_search_results(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        result = payload.get("result", [])

        if isinstance(result, dict):
            result = result.get("points", [])

        if not isinstance(result, list):
            return []

        return [item for item in result if isinstance(item, dict)]
