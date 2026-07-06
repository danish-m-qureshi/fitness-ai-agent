from datetime import UTC, date, datetime

from app.models.body_weight_log import BodyWeightLog
from app.models.meal import Meal
from app.models.user import User
from app.models.workout_session import WorkoutSession
from app.services.daily_summary_service import DailySummaryService


def test_generate_daily_summary_uses_user_targets(db_session) -> None:
    user = User(
        name="Summary User",
        email="summary@example.com",
        daily_calorie_target=2200,
        daily_protein_target_g=150,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    logged_at = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
    db_session.add_all(
        [
            Meal(
                user_id=user.id,
                description="chicken rice bowl",
                estimated_calories=600,
                estimated_protein_g=45,
                estimated_carbs_g=70,
                estimated_fat_g=12,
                source="test",
                created_at=logged_at,
            ),
            WorkoutSession(
                user_id=user.id,
                started_at=logged_at,
                notes="strength training",
            ),
            BodyWeightLog(
                user_id=user.id,
                weight_kg=82.5,
                logged_at=logged_at,
            ),
        ]
    )
    db_session.commit()

    service = DailySummaryService(db_session)
    summary = service.generate_daily_summary(
        user_id=user.id,
        summary_date=date(2026, 7, 5),
    )

    assert summary.total_calories == 600
    assert summary.calories_remaining == 1600
    assert summary.total_protein_g == 45
    assert summary.protein_remaining_g == 105
    assert summary.workouts_completed == 1
    assert summary.latest_weight_kg == 82.5
