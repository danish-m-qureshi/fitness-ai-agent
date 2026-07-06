from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AgentIntent = Literal[
    "meal_image",
    "meal_text",
    "workout_log",
    "weight_log",
    "summary_request",
    "email_summary",
    "general_chat",
    "unknown",
]

AgentStatus = Literal["completed", "needs_input", "error"]
AgentChannel = Literal["api", "whatsapp", "email", "scheduler"]


class AgentRequest(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    message_text: str | None = Field(default=None, max_length=4000)
    image_base64: str | None = None
    image_path: str | None = Field(default=None, max_length=1000)
    image_id: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=2000)
    channel: AgentChannel = "api"
    sender: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_input_present(self) -> "AgentRequest":
        if not (
            self.message_text
            or self.image_base64
            or self.image_path
            or self.image_id
            or self.image_url
        ):
            raise ValueError(
                "Provide message_text, image_base64, image_path, image_id, "
                "or image_url."
            )

        return self


class AgentMemorySnippet(BaseModel):
    memory_id: str
    memory_type: str
    content: str
    score: float | None = None
    source_table: str | None = None
    source_id: int | None = None


class AgentResponse(BaseModel):
    status: AgentStatus
    intent: AgentIntent
    response_text: str
    user_id: int | None = None
    meal_id: int | None = None
    workout_id: int | None = None
    weight_log_id: int | None = None
    daily_summary_id: int | None = None
    memories: list[AgentMemorySnippet] = Field(default_factory=list)
    tool_result: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    user_id: int | None = None
    channel: AgentChannel = "api"
    sender: str | None = None
    message_text: str | None = None
    image_base64: str | None = None
    image_path: str | None = None
    image_id: str | None = None
    image_url: str | None = None
    intent: AgentIntent = "unknown"
    memories: list[AgentMemorySnippet] = Field(default_factory=list)
    tool_result: dict[str, Any] = Field(default_factory=dict)
    response_text: str | None = None
    errors: list[str] = Field(default_factory=list)
    status: AgentStatus = "completed"
