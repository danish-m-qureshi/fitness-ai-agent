from app.api.deps import get_goal_service
from app.schemas.goal import GoalCreate, GoalResponse, GoalStatus, GoalUpdate
from app.services.goal_service import GoalService
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal: GoalCreate,
    goal_service: GoalService = Depends(get_goal_service),
) -> GoalResponse:
    return goal_service.create_goal(goal)


@router.get("", response_model=list[GoalResponse])
def list_goals(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    status_filter: GoalStatus | None = Query(default=None, alias="status"),
    goal_service: GoalService = Depends(get_goal_service),
) -> list[GoalResponse]:
    return goal_service.list_goals(
        skip=skip,
        limit=limit,
        user_id=user_id,
        status=status_filter,
    )


@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: int,
    goal_service: GoalService = Depends(get_goal_service),
) -> GoalResponse:
    return goal_service.get_goal(goal_id)


@router.patch("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    goal: GoalUpdate,
    goal_service: GoalService = Depends(get_goal_service),
) -> GoalResponse:
    return goal_service.update_goal(goal_id, goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    goal_service: GoalService = Depends(get_goal_service),
) -> Response:
    goal_service.delete_goal(goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
