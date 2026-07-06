import uuid
from datetime import UTC, datetime
from typing import Any

from app.schemas.memory import (
    MemoryCreate,
    MemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.services.memory.embedding_service import EmbeddingService
from app.services.memory.vector_store import QdrantVectorStore


class MemoryService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: QdrantVectorStore,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def create_memory(self, memory_data: MemoryCreate) -> MemoryResponse:
        return self._create_memory(memory_data)

    def _create_memory(
        self,
        memory_data: MemoryCreate,
        memory_id: str | None = None,
    ) -> MemoryResponse:
        memory_id = memory_id or str(uuid.uuid4())
        created_at = datetime.now(UTC)
        payload = {
            "user_id": memory_data.user_id,
            "memory_type": memory_data.memory_type,
            "content": memory_data.content.strip(),
            "metadata": memory_data.metadata,
            "source_table": memory_data.source_table,
            "source_id": memory_data.source_id,
            "created_at": created_at.isoformat(),
        }
        vector = self.embedding_service.embed_text(payload["content"])

        self.vector_store.upsert_memory(
            memory_id=memory_id,
            vector=vector,
            payload=payload,
        )

        return self._response_from_payload(memory_id, payload)

    def search_memories(
        self,
        search_data: MemorySearchRequest,
    ) -> MemorySearchResponse:
        query_vector = self.embedding_service.embed_text(search_data.query)
        results = self.vector_store.search_memory(
            vector=query_vector,
            limit=search_data.limit,
            user_id=search_data.user_id,
            memory_type=search_data.memory_type,
        )

        return MemorySearchResponse(
            results=[
                self._response_from_payload(
                    memory_id=str(result.get("id", "")),
                    payload=result.get("payload", {}),
                    score=result.get("score"),
                )
                for result in results
                if isinstance(result.get("payload"), dict)
            ]
        )

    def delete_memory(self, memory_id: str) -> None:
        self.vector_store.delete_memory(memory_id)

    def remember_meal(self, meal: Any) -> MemoryResponse | None:
        if meal.user_id is None:
            return None

        food_names = [
            food_item.name
            for food_item in getattr(meal, "food_items", [])
            if getattr(food_item, "name", None)
        ]
        macro_parts = [
            f"calories: {meal.estimated_calories}"
            if meal.estimated_calories is not None
            else None,
            f"protein: {meal.estimated_protein_g}g"
            if meal.estimated_protein_g is not None
            else None,
            f"carbs: {meal.estimated_carbs_g}g"
            if meal.estimated_carbs_g is not None
            else None,
            f"fat: {meal.estimated_fat_g}g"
            if meal.estimated_fat_g is not None
            else None,
        ]
        macros = ", ".join(part for part in macro_parts if part)
        foods = ", ".join(food_names)

        content_parts = [f"User logged meal: {meal.description}."]
        if foods:
            content_parts.append(f"Detected foods: {foods}.")
        if macros:
            content_parts.append(f"Estimated nutrition: {macros}.")
        if meal.nutrition_confidence:
            content_parts.append(f"Nutrition confidence: {meal.nutrition_confidence}.")

        return self.create_memory(
            MemoryCreate(
                user_id=meal.user_id,
                memory_type="meal",
                content=" ".join(content_parts),
                source_table="meals",
                source_id=meal.id,
                metadata={
                    "meal_id": meal.id,
                    "source": meal.source,
                    "image_path": getattr(meal, "image_path", None),
                    "analysis_status": getattr(meal, "analysis_status", None),
                },
            )
        )

    def remember_workout(self, workout: Any) -> MemoryResponse | None:
        if workout.user_id is None:
            return None

        content_parts = [f"User logged workout: {workout.name}."]
        if workout.duration_minutes is not None:
            content_parts.append(f"Duration: {workout.duration_minutes} minutes.")
        if workout.calories_burned is not None:
            content_parts.append(f"Calories burned: {workout.calories_burned}.")
        if workout.notes:
            content_parts.append(f"Notes: {workout.notes}.")

        return self.create_memory(
            MemoryCreate(
                user_id=workout.user_id,
                memory_type="workout",
                content=" ".join(content_parts),
                source_table="workouts",
                source_id=workout.id,
                metadata={
                    "workout_id": workout.id,
                    "performed_at": workout.performed_at.isoformat()
                    if workout.performed_at
                    else None,
                },
            )
        )

    def remember_workout_session(self, workout: Any) -> MemoryResponse | None:
        if workout.user_id is None:
            return None

        exercise_summaries: list[str] = []
        for exercise in getattr(workout, "exercises", []):
            set_summaries: list[str] = []
            for exercise_set in getattr(exercise, "sets", []):
                parts: list[str] = [f"set {exercise_set.set_number}"]
                if exercise_set.weight_kg is not None:
                    parts.append(f"{exercise_set.weight_kg:g}kg")
                if exercise_set.reps is not None:
                    parts.append(f"x {exercise_set.reps} reps")
                if exercise_set.duration_seconds is not None:
                    parts.append(f"{exercise_set.duration_seconds}s")

                set_summaries.append(" ".join(parts))

            if set_summaries:
                exercise_summaries.append(
                    f"{exercise.exercise_name}: {', '.join(set_summaries)}"
                )
            else:
                exercise_summaries.append(exercise.exercise_name)

        content_parts = ["User completed a workout session."]
        if workout.notes:
            content_parts.append(f"Notes: {workout.notes}.")
        if exercise_summaries:
            content_parts.append(f"Exercises: {'; '.join(exercise_summaries)}.")

        return self.create_memory(
            MemoryCreate(
                user_id=workout.user_id,
                memory_type="workout",
                content=" ".join(content_parts),
                source_table="workout_sessions",
                source_id=workout.id,
                metadata={
                    "workout_session_id": workout.id,
                    "started_at": workout.started_at.isoformat()
                    if workout.started_at
                    else None,
                    "ended_at": workout.ended_at.isoformat()
                    if workout.ended_at
                    else None,
                    "exercise_count": len(exercise_summaries),
                },
            )
        )

    def remember_daily_summary(self, summary: Any) -> MemoryResponse | None:
        if summary.user_id is None:
            return None

        content_parts = [
            f"Daily fitness summary for {summary.summary_date}",
            f"calories {summary.total_calories or 0}",
        ]

        if summary.calorie_target is not None:
            content_parts.append(f"target {summary.calorie_target}")
        if summary.calories_remaining is not None:
            content_parts.append(f"remaining {summary.calories_remaining}")
        if summary.total_protein_g is not None:
            content_parts.append(f"protein {summary.total_protein_g:g}g")
        if summary.workouts_completed:
            content_parts.append(f"workouts {summary.workouts_completed}")
        if summary.latest_weight_kg is not None:
            content_parts.append(f"weight {summary.latest_weight_kg:g}kg")
        if summary.coaching_suggestions:
            content_parts.append(f"coaching: {summary.coaching_suggestions}")

        memory_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                (
                    "fitness-ai-agent:daily_summary:"
                    f"{summary.user_id}:{summary.summary_date.isoformat()}"
                ),
            )
        )

        return self._create_memory(
            MemoryCreate(
                user_id=summary.user_id,
                memory_type="daily_summary",
                content=". ".join(content_parts),
                source_table="daily_summaries",
                source_id=summary.id,
                metadata={
                    "daily_summary_id": summary.id,
                    "summary_date": summary.summary_date.isoformat(),
                    "total_calories": summary.total_calories,
                    "calories_remaining": summary.calories_remaining,
                    "workouts_completed": summary.workouts_completed,
                },
            ),
            memory_id=memory_id,
        )

    def remember_body_weight_log(self, body_weight_log: Any) -> MemoryResponse | None:
        if body_weight_log.user_id is None:
            return None

        content_parts = [f"User logged body weight: {body_weight_log.weight_kg:g}kg."]
        if body_weight_log.notes:
            content_parts.append(f"Notes: {body_weight_log.notes}.")

        logged_at = getattr(body_weight_log, "logged_at", None)

        return self.create_memory(
            MemoryCreate(
                user_id=body_weight_log.user_id,
                memory_type="body_weight_log",
                content=" ".join(content_parts),
                source_table="body_weight_logs",
                source_id=body_weight_log.id,
                metadata={
                    "body_weight_log_id": body_weight_log.id,
                    "weight_kg": body_weight_log.weight_kg,
                    "logged_at": logged_at.isoformat() if logged_at else None,
                },
            )
        )

    def _response_from_payload(
        self,
        memory_id: str,
        payload: dict[str, Any],
        score: float | None = None,
    ) -> MemoryResponse:
        created_at_raw = payload.get("created_at")
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if isinstance(created_at_raw, str)
            else datetime.now(UTC)
        )

        return MemoryResponse(
            memory_id=memory_id,
            user_id=int(payload["user_id"]),
            memory_type=payload["memory_type"],
            content=payload["content"],
            metadata=payload.get("metadata") or {},
            source_table=payload.get("source_table"),
            source_id=payload.get("source_id"),
            created_at=created_at,
            score=score,
        )
