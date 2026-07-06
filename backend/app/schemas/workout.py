from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExerciseSetCreate(BaseModel):
    set_number: int = Field(..., ge=1)
    reps: int | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    rpe: float | None = Field(default=None, ge=0, le=10)
    is_warmup: bool = False

    @model_validator(mode="after")
    def validate_set_has_work(self) -> "ExerciseSetCreate":
        if (
            self.reps is None
            and self.weight_kg is None
            and self.duration_seconds is None
        ):
            raise ValueError("Exercise set must include reps, weight, or duration.")

        return self


class WorkoutExerciseCreate(BaseModel):
    exercise_catalog_id: int | None = Field(default=None, ge=1)
    exercise_name: str = Field(..., min_length=1, max_length=150)
    muscle_group: str | None = Field(default=None, max_length=100)
    order_index: int | None = Field(default=None, ge=0)
    notes: str | None = None
    sets: list[ExerciseSetCreate] = Field(default_factory=list)

    @field_validator("exercise_name")
    @classmethod
    def normalize_exercise_name(cls, value: str) -> str:
        return value.strip()


class WorkoutCreate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None
    exercises: list[WorkoutExerciseCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_time_range(self) -> "WorkoutCreate":
        if self.started_at and self.ended_at and self.ended_at < self.started_at:
            raise ValueError("Workout ended_at must be after started_at.")

        return self


class WorkoutUpdate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "WorkoutUpdate":
        if self.started_at and self.ended_at and self.ended_at < self.started_at:
            raise ValueError("Workout ended_at must be after started_at.")

        return self


class ExerciseSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_exercise_id: int
    set_number: int
    reps: int | None
    weight_kg: float | None
    duration_seconds: int | None
    rpe: float | None
    is_warmup: bool
    created_at: datetime


class WorkoutExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_session_id: int
    exercise_catalog_id: int | None
    exercise_name: str
    muscle_group: str | None
    order_index: int
    notes: str | None
    created_at: datetime
    sets: list[ExerciseSetResponse] = Field(default_factory=list)


class WorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    started_at: datetime | None
    ended_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    exercises: list[WorkoutExerciseResponse] = Field(default_factory=list)


class ExerciseCatalogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    primary_muscle: str | None = Field(default=None, max_length=100)
    secondary_muscles: str | None = None
    equipment: str | None = Field(default=None, max_length=100)
    instructions: str | None = None


class ExerciseCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    primary_muscle: str | None
    secondary_muscles: str | None
    equipment: str | None
    instructions: str | None
    created_at: datetime
    updated_at: datetime


class ExerciseBestSet(BaseModel):
    workout_session_id: int
    workout_exercise_id: int
    performed_at: datetime | None
    set_number: int
    reps: int | None
    weight_kg: float | None
    volume_kg: float
    estimated_1rm_kg: float | None


class WeeklyVolumePoint(BaseModel):
    week_start: date
    total_volume_kg: float


class ExerciseProgressResponse(BaseModel):
    exercise_name: str
    user_id: int | None = None
    total_sessions: int
    total_sets: int
    total_volume_kg: float
    best_estimated_1rm_kg: float | None
    best_set: ExerciseBestSet | None = None
    weekly_volume: list[WeeklyVolumePoint] = Field(default_factory=list)
    trend: str
