from app.schemas.memory import MemoryCreate, MemorySearchRequest
from app.services.memory.memory_service import MemoryService


class FakeEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        assert text
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def __init__(self) -> None:
        self.points: dict[str, dict] = {}

    def upsert_memory(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict,
    ) -> str:
        self.points[memory_id] = {"id": memory_id, "vector": vector, "payload": payload}
        return memory_id

    def search_memory(
        self,
        vector: list[float],
        limit: int,
        user_id: int,
        memory_type: str | None = None,
    ) -> list[dict]:
        results = []
        for point in self.points.values():
            payload = point["payload"]
            if payload["user_id"] != user_id:
                continue
            if memory_type is not None and payload["memory_type"] != memory_type:
                continue
            results.append(
                {
                    "id": point["id"],
                    "payload": payload,
                    "score": 1.0,
                }
            )
        return results[:limit]

    def delete_memory(self, memory_id: str) -> None:
        self.points.pop(memory_id, None)


def test_memory_create_and_search_round_trip() -> None:
    vector_store = FakeVectorStore()
    service = MemoryService(
        embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
        vector_store=vector_store,  # type: ignore[arg-type]
    )

    created = service.create_memory(
        MemoryCreate(
            user_id=1,
            memory_type="meal",
            content="User likes chicken biryani after workouts.",
            source_table="meals",
            source_id=10,
            metadata={"source": "test"},
        )
    )
    search = service.search_memories(
        MemorySearchRequest(user_id=1, query="biryani", memory_type="meal")
    )

    assert created.memory_id
    assert len(search.results) == 1
    assert search.results[0].source_id == 10
