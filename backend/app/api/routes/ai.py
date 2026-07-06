import base64
import binascii
import json
from typing import Any

from app.api.deps import (
    get_meal_image_analyzer,
    get_nutrition_service,
    get_vision_llm_client,
)
from app.core.exceptions import AppException
from app.schemas.ai import LLMHealthResponse, MealImageAnalysisResponse
from app.schemas.nutrition import DetectedFoodNutritionInput, NutritionEstimateRequest
from app.services.llm.base import VisionLLMClient
from app.services.nutrition_service import NutritionService
from app.services.vision.meal_image_analyzer import MealImageAnalyzer
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024


@router.get("/models/health", response_model=LLMHealthResponse)
async def get_model_health(
    vision_client: VisionLLMClient = Depends(get_vision_llm_client),
) -> LLMHealthResponse:
    return LLMHealthResponse.model_validate(await vision_client.health())


@router.post(
    "/analyze-meal-image",
    response_model=MealImageAnalysisResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["image_base64"],
                        "properties": {
                            "image_base64": {
                                "type": "string",
                                "description": "Base64-encoded image bytes.",
                            }
                        },
                    }
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "image": {
                                "type": "string",
                                "format": "binary",
                            },
                            "image_base64": {
                                "type": "string",
                                "description": "Alternative base64-encoded image bytes.",
                            },
                        },
                    }
                },
            },
        },
        "responses": {
            "400": {
                "description": "Missing or invalid image payload.",
            },
            "503": {
                "description": "Ollama is unavailable or the vision request failed.",
            },
        },
    },
)
async def analyze_meal_image(
    request: Request,
    meal_image_analyzer: MealImageAnalyzer = Depends(get_meal_image_analyzer),
    nutrition_service: NutritionService = Depends(get_nutrition_service),
) -> MealImageAnalysisResponse | JSONResponse:
    image_base64 = await _extract_image_base64(request)
    response = await meal_image_analyzer.analyze_image(image_base64)

    if not response.success:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )

    if response.analysis is not None:
        detected_foods = [
            DetectedFoodNutritionInput.model_validate(food.model_dump())
            for food in response.analysis.detected_foods
        ]
        response.nutrition_estimate = nutrition_service.estimate_nutrition(
            NutritionEstimateRequest(detected_foods=detected_foods)
        )

    return response


async def _extract_image_base64(request: Request) -> str:
    content_type = request.headers.get("content-type", "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_image = form.get("image") or form.get("file") or form.get("image_file")

        if isinstance(uploaded_image, UploadFile):
            return await _base64_from_upload(uploaded_image)

        image_base64 = form.get("image_base64")
        if isinstance(image_base64, str):
            return _validate_image_base64(image_base64)

    if "application/json" in content_type:
        payload = await _read_json_payload(request)
        image_base64 = payload.get("image_base64")

        if isinstance(image_base64, str):
            return _validate_image_base64(image_base64)

    raise AppException(
        message=(
            "Provide a meal image as multipart field 'image' or as "
            "JSON field 'image_base64'."
        ),
        status_code=400,
        error_code="meal_image_required",
    )


async def _read_json_payload(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise AppException(
            message="Request body must be valid JSON.",
            status_code=400,
            error_code="invalid_json",
        ) from exc

    if not isinstance(payload, dict):
        raise AppException(
            message="JSON payload must be an object.",
            status_code=400,
            error_code="invalid_json_payload",
        )

    return payload


async def _base64_from_upload(uploaded_image: UploadFile) -> str:
    if not uploaded_image.content_type or not uploaded_image.content_type.startswith(
        "image/"
    ):
        raise AppException(
            message="Uploaded file must be an image.",
            status_code=400,
            error_code="invalid_image_file",
        )

    image_bytes = await uploaded_image.read()

    if not image_bytes:
        raise AppException(
            message="Uploaded image is empty.",
            status_code=400,
            error_code="empty_image_file",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise AppException(
            message="Uploaded image is too large.",
            status_code=413,
            error_code="image_too_large",
        )

    return base64.b64encode(image_bytes).decode("utf-8")


def _validate_image_base64(image_base64: str) -> str:
    normalized = image_base64.strip()

    if normalized.startswith("data:image/") and "," in normalized:
        normalized = normalized.split(",", 1)[1]

    normalized = "".join(normalized.split())

    try:
        image_bytes = base64.b64decode(normalized, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppException(
            message="Image payload must be valid base64.",
            status_code=400,
            error_code="invalid_image_base64",
        ) from exc

    if not image_bytes:
        raise AppException(
            message="Image payload is empty.",
            status_code=400,
            error_code="empty_image_payload",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise AppException(
            message="Image payload is too large.",
            status_code=413,
            error_code="image_too_large",
        )

    return normalized
