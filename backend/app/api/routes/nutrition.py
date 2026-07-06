from app.api.deps import get_nutrition_service
from app.schemas.nutrition import (
    MealNutritionApplyRequest,
    MealNutritionResponse,
    NutritionEstimateRequest,
    NutritionEstimateResponse,
    NutritionFoodCreate,
    NutritionFoodResponse,
    NutritionFoodUpdate,
)
from app.services.nutrition_service import NutritionService
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.post("/estimate", response_model=NutritionEstimateResponse)
def estimate_nutrition(
    request: NutritionEstimateRequest,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> NutritionEstimateResponse:
    return nutrition_service.estimate_nutrition(request)


@router.post(
    "/foods",
    response_model=NutritionFoodResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_nutrition_food(
    food: NutritionFoodCreate,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> NutritionFoodResponse:
    return nutrition_service.create_food(food)


@router.get("/foods", response_model=list[NutritionFoodResponse])
def list_nutrition_foods(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    query: str | None = Query(default=None, min_length=1),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> list[NutritionFoodResponse]:
    return nutrition_service.list_foods(skip=skip, limit=limit, query=query)


@router.get("/foods/{food_id}", response_model=NutritionFoodResponse)
def get_nutrition_food(
    food_id: int,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> NutritionFoodResponse:
    return nutrition_service.get_food(food_id)


@router.patch("/foods/{food_id}", response_model=NutritionFoodResponse)
def update_nutrition_food(
    food_id: int,
    food: NutritionFoodUpdate,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> NutritionFoodResponse:
    return nutrition_service.update_food(food_id, food)


@router.delete("/foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_nutrition_food(
    food_id: int,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> Response:
    nutrition_service.delete_food(food_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/meals/{meal_id}/apply", response_model=MealNutritionResponse)
def apply_nutrition_to_meal(
    meal_id: int,
    request: MealNutritionApplyRequest,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> MealNutritionResponse:
    return nutrition_service.apply_nutrition_to_meal(meal_id, request)


@router.get("/meals/{meal_id}", response_model=MealNutritionResponse)
def get_meal_nutrition(
    meal_id: int,
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> MealNutritionResponse:
    return nutrition_service.get_meal_nutrition(meal_id)
