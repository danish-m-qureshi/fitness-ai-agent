from app.api.deps import get_body_weight_log_service
from app.schemas.body_weight_log import (
    BodyWeightLogCreate,
    BodyWeightLogResponse,
    BodyWeightLogUpdate,
)
from app.services.body_weight_log_service import BodyWeightLogService
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/body-weight-logs", tags=["body-weight-logs"])


@router.post(
    "",
    response_model=BodyWeightLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_body_weight_log(
    body_weight_log: BodyWeightLogCreate,
    body_weight_log_service: BodyWeightLogService = Depends(
        get_body_weight_log_service
    ),
) -> BodyWeightLogResponse:
    return body_weight_log_service.create_body_weight_log(body_weight_log)


@router.get("", response_model=list[BodyWeightLogResponse])
def list_body_weight_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    body_weight_log_service: BodyWeightLogService = Depends(
        get_body_weight_log_service
    ),
) -> list[BodyWeightLogResponse]:
    return body_weight_log_service.list_body_weight_logs(
        skip=skip,
        limit=limit,
        user_id=user_id,
    )


@router.get("/{log_id}", response_model=BodyWeightLogResponse)
def get_body_weight_log(
    log_id: int,
    body_weight_log_service: BodyWeightLogService = Depends(
        get_body_weight_log_service
    ),
) -> BodyWeightLogResponse:
    return body_weight_log_service.get_body_weight_log(log_id)


@router.patch("/{log_id}", response_model=BodyWeightLogResponse)
def update_body_weight_log(
    log_id: int,
    body_weight_log: BodyWeightLogUpdate,
    body_weight_log_service: BodyWeightLogService = Depends(
        get_body_weight_log_service
    ),
) -> BodyWeightLogResponse:
    return body_weight_log_service.update_body_weight_log(log_id, body_weight_log)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_body_weight_log(
    log_id: int,
    body_weight_log_service: BodyWeightLogService = Depends(
        get_body_weight_log_service
    ),
) -> Response:
    body_weight_log_service.delete_body_weight_log(log_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
