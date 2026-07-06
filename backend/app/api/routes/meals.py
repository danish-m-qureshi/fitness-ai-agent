from app.api.deps import (
    get_image_storage_service,
    get_meal_image_analyzer,
    get_meal_service,
    get_nutrition_service,
)
from app.schemas.meal import (
    MealCreate,
    MealImageAnalysisSaveResponse,
    MealResponse,
    MealTextRequest,
    MealTextResponse,
    MealUpdate,
)
from app.schemas.nutrition import DetectedFoodNutritionInput, NutritionEstimateRequest
from app.services.meal_service import MealService
from app.services.nutrition_service import NutritionService
from app.services.vision.image_storage import ImageStorageService
from app.services.vision.meal_image_analyzer import MealImageAnalyzer
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/meals", tags=["meals"])
CONFIDENCE_SCORES = {"low": 0.33, "medium": 0.66, "high": 0.9}


@router.post("", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create_meal(
    meal: MealCreate,
    meal_service: MealService = Depends(get_meal_service),
) -> MealResponse:
    return meal_service.create_meal(meal)


@router.post(
    "/text",
    response_model=MealTextResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_text_meal(
    meal: MealTextRequest,
    meal_service: MealService = Depends(get_meal_service),
) -> MealTextResponse:
    return meal_service.log_text_meal(meal)


@router.post(
    "/analyze-image",
    response_model=MealImageAnalysisSaveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_meal_image(
    file: UploadFile = File(...),
    user_id: int = Form(..., ge=1),
    meal_type: str | None = Form(default=None, max_length=50),
    image_storage_service: ImageStorageService = Depends(get_image_storage_service),
    meal_image_analyzer: MealImageAnalyzer = Depends(get_meal_image_analyzer),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
    meal_service: MealService = Depends(get_meal_service),
) -> MealImageAnalysisSaveResponse | JSONResponse:
    stored_image = await image_storage_service.save_meal_image(file)
    analysis_response = await meal_image_analyzer.analyze_image(
        stored_image.image_base64
    )

    if not analysis_response.success:
        error_status = _analysis_error_status(analysis_response.error)
        error_response = MealImageAnalysisSaveResponse(
            status=error_status,
            image_path=stored_image.path,
            error=analysis_response.error,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_response.model_dump(mode="json"),
        )

    analysis = analysis_response.analysis
    detected_foods = [
        DetectedFoodNutritionInput.model_validate(food.model_dump())
        for food in (analysis.detected_foods if analysis else [])
    ]
    nutrition_estimate = nutrition_service.estimate_nutrition(
        NutritionEstimateRequest(detected_foods=detected_foods)
    )
    description = _image_meal_description(meal_type, detected_foods)
    analysis_status = (
        "needs_clarification"
        if analysis and analysis.needs_user_clarification
        else "completed"
    )
    confidence_score = (
        CONFIDENCE_SCORES.get(analysis.overall_confidence)
        if analysis is not None
        else None
    )
    meal = meal_service.create_analyzed_image_meal(
        user_id=user_id,
        description=description,
        image_path=stored_image.path,
        analysis_status=analysis_status,
        analysis_raw_response=analysis_response.raw_response,
        confidence_score=confidence_score,
        nutrition_estimate=nutrition_estimate,
    )

    return MealImageAnalysisSaveResponse(
        status="success",
        meal=MealResponse.model_validate(meal),
        foods=nutrition_estimate.items,
        total_calories=nutrition_estimate.total_calories,
        total_protein_g=nutrition_estimate.total_protein_g,
        total_carbs_g=nutrition_estimate.total_carbs_g,
        total_fat_g=nutrition_estimate.total_fat_g,
        confidence=nutrition_estimate.confidence,
        notes=_nutrition_notes(nutrition_estimate.needs_user_clarification),
        analysis=analysis,
        nutrition_estimate=nutrition_estimate,
        image_path=stored_image.path,
    )


@router.get("", response_model=list[MealResponse])
def list_meals(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: int | None = Query(default=None, ge=1),
    meal_service: MealService = Depends(get_meal_service),
) -> list[MealResponse]:
    return meal_service.list_meals(skip=skip, limit=limit, user_id=user_id)


@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(
    meal_id: int,
    meal_service: MealService = Depends(get_meal_service),
) -> MealResponse:
    return meal_service.get_meal(meal_id)


@router.patch("/{meal_id}", response_model=MealResponse)
def update_meal(
    meal_id: int,
    meal: MealUpdate,
    meal_service: MealService = Depends(get_meal_service),
) -> MealResponse:
    return meal_service.update_meal(meal_id, meal)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: int,
    meal_service: MealService = Depends(get_meal_service),
) -> Response:
    meal_service.delete_meal(meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _analysis_error_status(error: str | None) -> str:
    if error and "model" in error.lower() and "missing" in error.lower():
        return "model_missing"

    return "model_not_ready"


def _image_meal_description(
    meal_type: str | None,
    detected_foods: list[DetectedFoodNutritionInput],
) -> str:
    names = [food.name.strip() for food in detected_foods if food.name.strip()]
    prefix = (
        f"{meal_type.strip()} meal" if meal_type and meal_type.strip() else "Image meal"
    )

    if names:
        return f"{prefix}: {', '.join(names)}"

    return f"{prefix}: no reliable food detections"


def _nutrition_notes(needs_user_clarification: bool) -> str:
    if needs_user_clarification:
        return "Estimate may vary based on portion size, ingredients, oil, and cooking method."

    return "Estimate is based on visible foods and the local nutrition catalog."
