from app.core.exceptions import ResourceNotFoundError
from app.models.user import User
from sqlalchemy.orm import Session


def ensure_user_exists(db: Session, user_id: int | None) -> None:
    if user_id is None:
        return

    if db.get(User, user_id) is None:
        raise ResourceNotFoundError("User")
