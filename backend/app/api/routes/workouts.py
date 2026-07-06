from app.api.deps import get_workout_service
from app.schemas.workout import (
    ExerciseProgressResponse,
    ExerciseSetCreate,
    ExerciseSetResponse,
    WorkoutCreate,
    WorkoutExerciseCreate,
    WorkoutExerciseResponse,
    WorkoutResponse,
    WorkoutUpdate,
)
from app.services.workout_service import WorkoutService
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout: WorkoutCreate,
    workout_service: WorkoutService = Depends(get_workout_service),
) -> WorkoutResponse:
    return workout_service.create_workout(workout)


@router.get("", response_model=list[WorkoutResponse])
def list_workouts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    workout_service: WorkoutService = Depends(get_workout_service),
) -> list[WorkoutResponse]:
    return workout_service.list_workouts(
        skip=skip,
        limit=limit,
        user_id=user_id,
    )


@router.get("/progress/{exercise_name}", response_model=ExerciseProgressResponse)
def get_exercise_progress(
    exercise_name: str,
    user_id: int | None = Query(default=None, ge=1),
    workout_service: WorkoutService = Depends(get_workout_service),
) -> ExerciseProgressResponse:
    return workout_service.get_exercise_progress(
        exercise_name=exercise_name,
        user_id=user_id,
    )


@router.get("/{workout_id}", response_model=WorkoutResponse)
def get_workout(
    workout_id: int,
    workout_service: WorkoutService = Depends(get_workout_service),
) -> WorkoutResponse:
    return workout_service.get_workout(workout_id)


@router.patch("/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: int,
    workout: WorkoutUpdate,
    workout_service: WorkoutService = Depends(get_workout_service),
) -> WorkoutResponse:
    return workout_service.update_workout(workout_id, workout)


@router.post(
    "/{workout_id}/exercises",
    response_model=WorkoutExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_exercise(
    workout_id: int,
    exercise: WorkoutExerciseCreate,
    workout_service: WorkoutService = Depends(get_workout_service),
) -> WorkoutExerciseResponse:
    return workout_service.add_exercise(workout_id, exercise)


@router.post(
    "/{workout_id}/exercises/{exercise_id}/sets",
    response_model=ExerciseSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_set(
    workout_id: int,
    exercise_id: int,
    exercise_set: ExerciseSetCreate,
    workout_service: WorkoutService = Depends(get_workout_service),
) -> ExerciseSetResponse:
    return workout_service.add_set(workout_id, exercise_id, exercise_set)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    workout_service: WorkoutService = Depends(get_workout_service),
) -> Response:
    workout_service.delete_workout(workout_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
