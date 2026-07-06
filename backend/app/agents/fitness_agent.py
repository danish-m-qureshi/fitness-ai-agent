import base64
import binascii
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.exceptions import AppException
from app.schemas.agent import (
    AgentMemorySnippet,
    AgentRequest,
    AgentResponse,
    AgentState,
)
from app.schemas.body_weight_log import BodyWeightLogCreate, BodyWeightLogResponse
from app.schemas.daily_summary import DailySummaryResponse
from app.schemas.meal import MealCreate, MealResponse
from app.schemas.memory import MemoryCreate, MemorySearchRequest
from app.schemas.nutrition import DetectedFoodNutritionInput, NutritionEstimateRequest
from app.schemas.workout import (
    ExerciseSetCreate,
    WorkoutCreate,
    WorkoutExerciseCreate,
    WorkoutResponse,
)
from app.services.body_weight_log_service import BodyWeightLogService
from app.services.daily_summary_service import DailySummaryService
from app.services.email.email_service import EmailService
from app.services.meal_service import MealService
from app.services.memory.memory_service import MemoryService
from app.services.nutrition_service import NutritionService
from app.services.user_service import UserService
from app.services.vision.meal_image_analyzer import MealImageAnalyzer
from app.services.workout_service import WorkoutService

logger = logging.getLogger(__name__)


class FitnessAgent:
    def __init__(
        self,
        meal_service: MealService,
        workout_service: WorkoutService,
        body_weight_log_service: BodyWeightLogService,
        daily_summary_service: DailySummaryService,
        memory_service: MemoryService,
        nutrition_service: NutritionService,
        user_service: UserService,
        email_service: EmailService,
        meal_image_analyzer: MealImageAnalyzer | None = None,
    ) -> None:
        self.meal_service = meal_service
        self.workout_service = workout_service
        self.body_weight_log_service = body_weight_log_service
        self.daily_summary_service = daily_summary_service
        self.memory_service = memory_service
        self.nutrition_service = nutrition_service
        self.user_service = user_service
        self.email_service = email_service
        self.meal_image_analyzer = meal_image_analyzer

    async def run(self, request: AgentRequest) -> AgentResponse:
        state = self._receive_message(request)
        self._classify_intent(state)
        self._retrieve_memory(state)
        await self._route_task(state)
        self._store_agent_note(state)
        return self._response(state)

    def _receive_message(self, request: AgentRequest) -> AgentState:
        return AgentState(
            user_id=request.user_id,
            channel=request.channel,
            sender=request.sender,
            message_text=request.message_text,
            image_base64=request.image_base64,
            image_path=request.image_path,
            image_id=request.image_id,
            image_url=request.image_url,
        )

    def _classify_intent(self, state: AgentState) -> None:
        if state.image_base64 or state.image_path or state.image_id or state.image_url:
            state.intent = "meal_image"
            return

        text = self._normalized_text(state)
        if not text:
            state.intent = "unknown"
            return

        if self._is_summary_request(text):
            if self._is_email_summary_request(text):
                state.intent = "email_summary"
                return

            state.intent = "summary_request"
            return

        if self._parse_weight_text(text) is not None:
            state.intent = "weight_log"
            return

        if self._parse_workout_text(text) is not None:
            state.intent = "workout_log"
            return

        if self._is_meal_text(text):
            state.intent = "meal_text"
            return

        state.intent = "general_chat"

    def _retrieve_memory(self, state: AgentState) -> None:
        if state.user_id is None:
            return

        query = self._memory_query(state)
        if not query:
            return

        try:
            results = self.memory_service.search_memories(
                MemorySearchRequest(
                    user_id=state.user_id,
                    query=query,
                    limit=5,
                )
            )
        except Exception as exc:
            logger.warning("Agent memory retrieval failed: %s", exc)
            state.errors.append("Memory retrieval was unavailable.")
            return

        state.memories = [
            AgentMemorySnippet(
                memory_id=result.memory_id,
                memory_type=result.memory_type,
                content=result.content,
                score=result.score,
                source_table=result.source_table,
                source_id=result.source_id,
            )
            for result in results.results
        ]

    async def _route_task(self, state: AgentState) -> None:
        try:
            if state.intent == "meal_text":
                self._handle_meal_text(state)
            elif state.intent == "workout_log":
                self._handle_workout_log(state)
            elif state.intent == "weight_log":
                self._handle_weight_log(state)
            elif state.intent == "summary_request":
                self._handle_summary_request(state)
            elif state.intent == "email_summary":
                self._handle_email_summary(state)
            elif state.intent == "meal_image":
                await self._handle_meal_image(state)
            elif state.intent == "general_chat":
                self._handle_general_chat(state)
            else:
                self._handle_unknown(state)
        except AppException as exc:
            state.status = "needs_input" if exc.status_code < 500 else "error"
            state.errors.append(exc.message)
            state.response_text = exc.message
        except Exception as exc:
            logger.exception("Agent task failed")
            state.status = "error"
            state.errors.append(str(exc))
            state.response_text = (
                "I hit a local service error while handling that. "
                "Try again after checking health."
            )

    def _handle_meal_text(self, state: AgentState) -> None:
        if state.user_id is None:
            self._needs_user_id(state, "meal")
            return

        description = self._clean_meal_text(state.message_text or "")
        meal = self.meal_service.create_meal(
            MealCreate(
                user_id=state.user_id,
                description=description,
                source=state.channel,
            )
        )
        state.tool_result = MealResponse.model_validate(meal).model_dump(mode="json")
        state.response_text = self._with_memory_context(
            state,
            f"Meal logged: {meal.description}.",
        )

    def _handle_workout_log(self, state: AgentState) -> None:
        if state.user_id is None:
            self._needs_user_id(state, "workout")
            return

        parsed_workout = self._parse_workout_text(state.message_text or "")
        if parsed_workout is None:
            state.status = "needs_input"
            state.response_text = (
                "I recognized a workout, but I need sets, exercise, weight, and reps. "
                "Try: 'Logged 3 sets bench press 50kg x 10'."
            )
            return

        workout = self.workout_service.create_workout(
            WorkoutCreate(
                user_id=state.user_id,
                started_at=datetime.now(UTC),
                notes=f"Logged by agent from {state.channel}.",
                exercises=[parsed_workout],
            )
        )
        exercise = workout.exercises[0] if workout.exercises else None
        progress = (
            self.workout_service.get_exercise_progress(
                exercise.exercise_name,
                user_id=state.user_id,
            )
            if exercise is not None
            else None
        )
        state.tool_result = WorkoutResponse.model_validate(workout).model_dump(
            mode="json"
        )

        if progress is None:
            state.response_text = f"Workout logged: session {workout.id}."
            return

        state.response_text = (
            f"Workout logged: {exercise.exercise_name}. "
            f"You now have {progress.total_sets} logged sets and "
            f"{progress.total_volume_kg:g}kg total volume for this exercise."
        )

    def _handle_weight_log(self, state: AgentState) -> None:
        if state.user_id is None:
            self._needs_user_id(state, "weight log")
            return

        weight_kg = self._parse_weight_text(state.message_text or "")
        if weight_kg is None:
            state.status = "needs_input"
            state.response_text = (
                "I recognized a weight log, but could not find the weight."
            )
            return

        body_weight_log = self.body_weight_log_service.create_body_weight_log(
            BodyWeightLogCreate(
                user_id=state.user_id,
                weight_kg=weight_kg,
                notes=f"Logged by agent from {state.channel}.",
                logged_at=datetime.now(UTC),
            )
        )
        self._remember_body_weight_log(body_weight_log)
        state.tool_result = BodyWeightLogResponse.model_validate(
            body_weight_log
        ).model_dump(mode="json")
        state.response_text = f"Weight logged: {weight_kg:g}kg."

    def _handle_summary_request(self, state: AgentState) -> None:
        if state.user_id is None:
            self._needs_user_id(state, "daily summary")
            return

        summary = self.daily_summary_service.generate_daily_summary(
            user_id=state.user_id,
            summary_date=datetime.now(UTC).date(),
        )
        summary_payload = DailySummaryResponse.model_validate(summary).model_dump(
            mode="json"
        )
        state.tool_result = summary_payload
        state.response_text = self._summary_response(summary_payload)

    def _handle_email_summary(self, state: AgentState) -> None:
        if state.user_id is None:
            self._needs_user_id(state, "daily summary email")
            return

        summary = self.daily_summary_service.generate_daily_summary(
            user_id=state.user_id,
            summary_date=datetime.now(UTC).date(),
        )
        user = self.user_service.get_user(state.user_id)
        result = self.email_service.send_daily_summary(
            summary=summary,
            user=user,
            to_email=self._extract_email_address(state.message_text or ""),
        )

        if result.status == "sent":
            summary = self.daily_summary_service.mark_email_sent(summary.id)

        summary_payload = DailySummaryResponse.model_validate(summary).model_dump(
            mode="json"
        )
        state.tool_result = {
            "email_status": result.status,
            "recipient": result.recipient,
            "subject": result.subject,
            "reason": result.reason,
            "summary": summary_payload,
            "id": summary_payload["id"],
        }

        status_text = {
            "sent": "Daily summary email sent",
            "dry_run": "Daily summary email dry-run prepared",
            "skipped": "Daily summary email was not sent",
        }[result.status]
        reason_text = f" {result.reason}" if result.reason else ""
        recipient_text = f" for {result.recipient}" if result.recipient else ""
        state.response_text = (
            f"{status_text}{recipient_text}.{reason_text} "
            f"{self._summary_response(summary_payload)}"
        ).strip()

        if result.status == "skipped":
            state.status = "needs_input"

    async def _handle_meal_image(self, state: AgentState) -> None:
        if state.user_id is None:
            self._needs_user_id(state, "meal image")
            return

        if not state.image_base64 and not state.image_path:
            state.status = "needs_input"
            state.response_text = (
                "I recognized a meal image, but I need image_base64 or a local "
                "image_path. WhatsApp media IDs and URLs must be downloaded before "
                "local analysis."
            )
            return

        if self.meal_image_analyzer is None:
            state.status = "error"
            state.response_text = "Meal image analysis is not configured."
            return

        image_base64 = self._image_base64(state)
        if image_base64 is None:
            state.status = "needs_input"
            state.response_text = (
                "I recognized a meal image, but I need image_base64 or a local "
                "image_path. WhatsApp media IDs and URLs must be downloaded before "
                "local analysis."
            )
            return

        analysis_response = await self.meal_image_analyzer.analyze_image(image_base64)
        if not analysis_response.success:
            state.status = "error"
            state.errors.append(
                analysis_response.error or "Meal image analysis failed."
            )
            state.response_text = (
                "I could not analyze that meal image locally. "
                f"{analysis_response.error or 'Check the Ollama vision model.'}"
            )
            return

        analysis = analysis_response.analysis
        detected_foods = [
            DetectedFoodNutritionInput.model_validate(food.model_dump())
            for food in (analysis.detected_foods if analysis else [])
        ]
        nutrition_estimate = self.nutrition_service.estimate_nutrition(
            NutritionEstimateRequest(detected_foods=detected_foods)
        )
        meal = self.meal_service.create_analyzed_image_meal(
            user_id=state.user_id,
            description=self._image_meal_description(detected_foods),
            image_path=state.image_path or "inline://agent",
            analysis_status=(
                "needs_clarification"
                if analysis and analysis.needs_user_clarification
                else "completed"
            ),
            analysis_raw_response=analysis_response.raw_response,
            confidence_score=self._confidence_score(
                analysis.overall_confidence if analysis else None
            ),
            nutrition_estimate=nutrition_estimate,
        )
        state.tool_result = MealResponse.model_validate(meal).model_dump(mode="json")
        state.response_text = (
            f"Meal image logged: {meal.description}. "
            f"Estimated {nutrition_estimate.total_calories or 0} calories and "
            f"{nutrition_estimate.total_protein_g or 0:g}g protein. "
            "This is an estimate, not medical advice."
        )

    def _handle_general_chat(self, state: AgentState) -> None:
        memory_sentence = ""
        if state.memories:
            memory_sentence = f" I found a related note: {state.memories[0].content}"

        state.response_text = (
            "I can log meals, analyze meal images, track workouts, log body weight, "
            "and generate daily summaries."
            f"{memory_sentence}"
        )

    def _handle_unknown(self, state: AgentState) -> None:
        state.status = "needs_input"
        state.response_text = (
            "I could not understand that yet. Try a meal, workout, body weight, "
            "meal image, or daily summary request."
        )

    def _store_agent_note(self, state: AgentState) -> None:
        if (
            state.user_id is None
            or state.intent not in {"general_chat", "unknown"}
            or not state.message_text
            or not state.response_text
        ):
            return

        try:
            self.memory_service.create_memory(
                MemoryCreate(
                    user_id=state.user_id,
                    memory_type="agent_note",
                    content=(
                        f"User asked the fitness agent: {state.message_text}. "
                        f"Agent replied: {state.response_text}"
                    ),
                    source_table=None,
                    source_id=None,
                    metadata={
                        "intent": state.intent,
                        "channel": state.channel,
                    },
                )
            )
        except Exception as exc:
            logger.warning("Agent note memory store failed: %s", exc)
            state.errors.append("Agent note memory was not stored.")

    def _response(self, state: AgentState) -> AgentResponse:
        return AgentResponse(
            status=state.status,
            intent=state.intent,
            response_text=state.response_text or "",
            user_id=state.user_id,
            meal_id=(
                state.tool_result.get("id")
                if state.intent in {"meal_text", "meal_image"}
                else None
            ),
            workout_id=(
                state.tool_result.get("id") if state.intent == "workout_log" else None
            ),
            weight_log_id=(
                state.tool_result.get("id") if state.intent == "weight_log" else None
            ),
            daily_summary_id=(
                state.tool_result.get("id")
                if state.intent in {"summary_request", "email_summary"}
                else None
            ),
            memories=state.memories,
            tool_result=state.tool_result,
            errors=state.errors,
        )

    def _normalized_text(self, state: AgentState) -> str:
        return (state.message_text or "").lower().strip()

    def _memory_query(self, state: AgentState) -> str:
        if state.message_text:
            return state.message_text
        if state.image_base64 or state.image_path or state.image_id or state.image_url:
            return "recent meals nutrition preferences"
        return ""

    def _is_summary_request(self, text: str) -> bool:
        return any(
            phrase in text
            for phrase in [
                "summary",
                "calories today",
                "protein today",
                "how am i doing",
                "how did i do",
                "today's progress",
                "todays progress",
            ]
        )

    def _is_email_summary_request(self, text: str) -> bool:
        return "email" in text and any(
            phrase in text
            for phrase in [
                "summary",
                "daily summary",
                "today's progress",
                "todays progress",
            ]
        )

    def _is_meal_text(self, text: str) -> bool:
        return any(
            phrase in text
            for phrase in [
                "i ate",
                "i had",
                "ate ",
                "breakfast",
                "lunch",
                "dinner",
                "snack",
                "meal",
            ]
        )

    def _parse_workout_text(self, text: str) -> WorkoutExerciseCreate | None:
        patterns = [
            re.compile(
                r"(?P<sets>\d+)\s*(?:sets?|x)\s+"
                r"(?P<exercise>[a-z][a-z\s-]*?)\s+"
                r"(?P<weight>\d+(?:\.\d+)?)\s*kg\s*"
                r"(?:x|for)?\s*(?P<reps>\d+)\s*(?:reps?)?",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?P<exercise>[a-z][a-z\s-]*?)\s+"
                r"(?P<weight>\d+(?:\.\d+)?)\s*kg\s+"
                r"(?P<sets>\d+)\s*(?:sets?|x)\s*(?:of)?\s*"
                r"(?P<reps>\d+)\s*(?:reps?)?",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?P<exercise>[a-z][a-z\s-]*?)\s+"
                r"(?P<weight>\d+(?:\.\d+)?)\s*kg\s*"
                r"(?:x|for)\s*(?P<reps>\d+)\s*"
                r"(?:for\s*)?(?P<sets>\d+)\s*sets?",
                re.IGNORECASE,
            ),
        ]

        for pattern in patterns:
            match = pattern.search(text)
            if match is None:
                continue

            sets_count = min(int(match.group("sets")), 20)
            reps = int(match.group("reps"))
            weight_kg = float(match.group("weight"))
            exercise_name = self._clean_exercise_name(match.group("exercise"))

            return WorkoutExerciseCreate(
                exercise_name=exercise_name,
                sets=[
                    ExerciseSetCreate(
                        set_number=set_number,
                        reps=reps,
                        weight_kg=weight_kg,
                    )
                    for set_number in range(1, sets_count + 1)
                ],
            )

        return None

    def _parse_weight_text(self, text: str) -> float | None:
        if not re.search(r"\b(weight|weigh|weighed|scale)\b", text, re.IGNORECASE):
            return None

        match = re.search(
            r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs|kilograms?|lb|lbs|pounds?)\b",
            text,
            re.IGNORECASE,
        )
        if match is None:
            return None

        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit in {"lb", "lbs", "pound", "pounds"}:
            value = value * 0.45359237

        return round(value, 1)

    def _clean_meal_text(self, text: str) -> str:
        cleaned = re.sub(r"^\s*i\s+(ate|had)\s+", "", text, flags=re.IGNORECASE)
        return cleaned.strip() or text.strip()

    def _clean_exercise_name(self, value: str) -> str:
        cleaned = value.lower().strip()
        cleaned = re.sub(r"^(logged|did|completed)\s+", "", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _extract_email_address(self, text: str) -> str | None:
        match = re.search(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            text,
            flags=re.IGNORECASE,
        )
        return match.group(0) if match else None

    def _needs_user_id(self, state: AgentState, action: str) -> None:
        state.status = "needs_input"
        state.response_text = f"I can handle that {action}, but I need a user_id."

    def _with_memory_context(self, state: AgentState, response: str) -> str:
        if not state.memories:
            return response

        return f"{response} I also found related context in memory."

    def _summary_response(self, summary: dict[str, Any]) -> str:
        calories = summary.get("total_calories") or 0
        protein = summary.get("total_protein_g") or 0
        workouts = summary.get("workouts_completed") or 0
        remaining = summary.get("calories_remaining")
        suggestions = summary.get("coaching_suggestions") or ""

        remaining_text = (
            f" {remaining} calories remaining." if remaining is not None else ""
        )
        return (
            f"Today: {calories} calories, {protein:g}g protein, "
            f"{workouts} workouts logged.{remaining_text} {suggestions}"
        ).strip()

    def _image_base64(self, state: AgentState) -> str | None:
        if state.image_base64:
            return self._normalize_image_base64(state.image_base64)

        if not state.image_path:
            return None

        path = Path(state.image_path)
        if not path.exists() or not path.is_file():
            raise AppException(
                message="Image path does not exist on the backend filesystem.",
                status_code=400,
                error_code="agent_image_path_not_found",
            )

        return base64.b64encode(path.read_bytes()).decode("utf-8")

    def _normalize_image_base64(self, image_base64: str) -> str:
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
                error_code="invalid_agent_image_base64",
            ) from exc

        if not image_bytes:
            raise AppException(
                message="Image payload is empty.",
                status_code=400,
                error_code="empty_agent_image_payload",
            )

        return normalized

    def _image_meal_description(
        self,
        detected_foods: list[DetectedFoodNutritionInput],
    ) -> str:
        names = [food.name.strip() for food in detected_foods if food.name.strip()]
        if names:
            return f"Agent image meal: {', '.join(names)}"

        return "Agent image meal: no reliable food detections"

    def _confidence_score(self, confidence: str | None) -> float | None:
        return {"low": 0.33, "medium": 0.66, "high": 0.9}.get(confidence or "")

    def _remember_body_weight_log(self, body_weight_log: Any) -> None:
        try:
            self.memory_service.remember_body_weight_log(body_weight_log)
        except Exception as exc:
            logger.warning("Body weight memory store failed: %s", exc)
