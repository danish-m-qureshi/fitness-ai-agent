import json
import logging

from app.schemas.ai import MealImageAnalysis, MealImageAnalysisResponse
from app.services.llm.base import VisionLLMClient, VisionLLMError
from app.services.vision.prompt_templates import MEAL_IMAGE_PROMPT
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class MealImageAnalyzer:
    def __init__(self, vision_client: VisionLLMClient, model: str) -> None:
        self.vision_client = vision_client
        self.model = model

    async def analyze_image(self, image_base64: str) -> MealImageAnalysisResponse:
        try:
            llm_response = await self.vision_client.analyze_image(
                image_base64=image_base64,
                prompt=MEAL_IMAGE_PROMPT,
            )
        except VisionLLMError as exc:
            return MealImageAnalysisResponse(
                success=False,
                model=self.model,
                analysis=None,
                raw_response=None,
                error=str(exc),
            )

        raw_response = str(llm_response.get("raw_response", ""))
        analysis = self._parse_analysis(raw_response)

        return MealImageAnalysisResponse(
            success=True,
            model=self.model,
            analysis=analysis,
            raw_response=raw_response,
            error=None,
        )

    def _parse_analysis(self, raw_response: str) -> MealImageAnalysis:
        try:
            payload = self._loads_json_object(raw_response)
            analysis = MealImageAnalysis.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, ValueError):
            logger.warning("Vision model returned invalid meal analysis JSON")
            return self._fallback_analysis()

        if analysis.needs_user_clarification and not analysis.clarifying_questions:
            analysis.clarifying_questions.append(
                "Can you share the portion size and cooking method?"
            )

        return analysis

    def _loads_json_object(self, raw_response: str) -> dict:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError:
            start = raw_response.find("{")
            end = raw_response.rfind("}")

            if start == -1 or end == -1 or end <= start:
                raise

            payload = json.loads(raw_response[start : end + 1])

        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object from vision model.")

        return payload

    def _fallback_analysis(self) -> MealImageAnalysis:
        return MealImageAnalysis(
            detected_foods=[],
            overall_confidence="low",
            needs_user_clarification=True,
            clarifying_questions=[
                "I could not reliably parse the meal image. Can you describe what is on the plate?"
            ],
        )
