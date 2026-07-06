class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "app_error",
        details: dict | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class MealDescriptionTooVagueError(AppException):
    def __init__(self) -> None:
        super().__init__(
            message="Meal description is too vague. Please describe what you ate.",
            status_code=422,
            error_code="meal_description_too_vague",
        )


class ResourceNotFoundError(AppException):
    def __init__(self, resource_name: str) -> None:
        super().__init__(
            message=f"{resource_name} not found.",
            status_code=404,
            error_code=f"{resource_name.lower().replace(' ', '_')}_not_found",
        )


class ResourceConflictError(AppException):
    def __init__(self, message: str, error_code: str = "resource_conflict") -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code,
        )
