from app.api.deps import get_memory_service
from app.schemas.memory import (
    MemoryCreate,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.services.memory.memory_service import MemoryService
from fastapi import APIRouter, Depends, Response, status

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(
    memory: MemoryCreate,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    return memory_service.create_memory(memory)


@router.post("/search", response_model=MemorySearchResponse)
def search_memory(
    search: MemorySearchRequest,
    memory_service: MemoryService = Depends(get_memory_service),
) -> MemorySearchResponse:
    return memory_service.search_memories(search)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    memory_service: MemoryService = Depends(get_memory_service),
) -> Response:
    memory_service.delete_memory(memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
