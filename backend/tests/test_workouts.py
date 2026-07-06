from app.models.user import User
from app.schemas.workout import ExerciseSetCreate, WorkoutCreate, WorkoutExerciseCreate
from app.services.workout_service import WorkoutService


def test_workout_progress_calculates_volume_and_best_set(db_session) -> None:
    user = User(name="Workout User", email="workout@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    service = WorkoutService(db_session)
    service.create_workout(
        WorkoutCreate(
            user_id=user.id,
            exercises=[
                WorkoutExerciseCreate(
                    exercise_name="bench press",
                    sets=[
                        ExerciseSetCreate(set_number=1, reps=10, weight_kg=50),
                        ExerciseSetCreate(set_number=2, reps=5, weight_kg=60),
                    ],
                )
            ],
        )
    )

    progress = service.get_exercise_progress("bench press", user_id=user.id)

    assert progress.total_sessions == 1
    assert progress.total_sets == 2
    assert progress.total_volume_kg == 800
    assert progress.best_estimated_1rm_kg == 70
