import pytest
from app.core.exceptions import MealDescriptionTooVagueError
from app.services.meal_service import MealService


def test_meal_description_rejects_vague_input() -> None:
    service = MealService(db=None)  # type: ignore[arg-type]

    with pytest.raises(MealDescriptionTooVagueError):
        service._validate_description("food")


def test_meal_description_accepts_specific_input() -> None:
    service = MealService(db=None)  # type: ignore[arg-type]

    service._validate_description("chicken biryani")
