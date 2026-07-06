from datetime import datetime

from app.core.phone_numbers import normalize_phone_number
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserPhoneNumberMixin(BaseModel):
    @field_validator("phone_number", mode="before", check_fields=False)
    @classmethod
    def normalize_phone_number_field(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            return normalize_phone_number(value)

        return value


class UserCreate(UserPhoneNumberMixin):
    name: str = Field(..., min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=50)
    age: int | None = Field(default=None, ge=0, le=130)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=1000)
    goal_weight_kg: float | None = Field(default=None, gt=0, le=1000)
    activity_level: str | None = Field(default=None, max_length=50)
    fitness_goal: str | None = Field(default=None, max_length=100)
    daily_calorie_target: int | None = Field(default=None, ge=0, le=20000)
    daily_protein_target_g: float | None = Field(default=None, ge=0, le=1000)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)


class UserUpdate(UserPhoneNumberMixin):
    name: str = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=50)
    age: int | None = Field(default=None, ge=0, le=130)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=1000)
    goal_weight_kg: float | None = Field(default=None, gt=0, le=1000)
    activity_level: str | None = Field(default=None, max_length=50)
    fitness_goal: str | None = Field(default=None, max_length=100)
    daily_calorie_target: int | None = Field(default=None, ge=0, le=20000)
    daily_protein_target_g: float | None = Field(default=None, ge=0, le=1000)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)


class UserProfileUpdate(UserPhoneNumberMixin):
    phone_number: str | None = Field(default=None, max_length=50)
    age: int | None = Field(default=None, ge=0, le=130)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=1000)
    goal_weight_kg: float | None = Field(default=None, gt=0, le=1000)
    activity_level: str | None = Field(default=None, max_length=50)
    fitness_goal: str | None = Field(default=None, max_length=100)
    daily_calorie_target: int | None = Field(default=None, ge=0, le=20000)
    daily_protein_target_g: float | None = Field(default=None, ge=0, le=1000)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    phone_number: str | None
    age: int | None
    height_cm: float | None
    weight_kg: float | None
    goal_weight_kg: float | None
    activity_level: str | None
    fitness_goal: str | None
    daily_calorie_target: int | None
    daily_protein_target_g: float | None
    timezone: str
    created_at: datetime
    updated_at: datetime
