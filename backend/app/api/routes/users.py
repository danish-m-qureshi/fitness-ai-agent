from app.api.deps import get_user_service
from app.schemas.user import UserCreate, UserProfileUpdate, UserResponse, UserUpdate
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return user_service.create_user(user)


@router.get("", response_model=list[UserResponse])
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user_service: UserService = Depends(get_user_service),
) -> list[UserResponse]:
    return user_service.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return user_service.get_user(user_id)


@router.get("/{user_id}/profile", response_model=UserResponse)
def get_user_profile(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return user_service.get_profile(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return user_service.update_user(user_id, user)


@router.patch("/{user_id}/profile", response_model=UserResponse)
def update_user_profile(
    user_id: int,
    profile: UserProfileUpdate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    return user_service.update_profile(user_id, profile)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
) -> Response:
    user_service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
