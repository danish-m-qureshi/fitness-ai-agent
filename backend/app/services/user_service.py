from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.core.phone_numbers import normalize_phone_number
from app.models.user import User
from app.schemas.user import UserCreate, UserProfileUpdate, UserUpdate
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(self, user_data: UserCreate) -> User:
        user = User(**user_data.model_dump())
        self.db.add(user)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                message="User with this email already exists.",
                error_code="user_email_already_exists",
            ) from exc

        self.db.refresh(user)
        return user

    def list_users(self, skip: int = 0, limit: int = 50) -> list[User]:
        statement = select(User).offset(skip).limit(limit).order_by(User.id)
        return list(self.db.scalars(statement).all())

    def get_user(self, user_id: int) -> User:
        user = self.db.get(User, user_id)

        if user is None:
            raise ResourceNotFoundError("User")

        return user

    def get_user_by_phone_number(self, phone_number: str) -> User | None:
        normalized_phone_number = normalize_phone_number(phone_number)
        if normalized_phone_number is None:
            return None

        statement = select(User).where(User.phone_number == normalized_phone_number)
        user = self.db.scalars(statement).first()
        if user is not None:
            return user

        users_with_phone = self.db.scalars(
            select(User).where(User.phone_number.is_not(None))
        ).all()
        for candidate in users_with_phone:
            if (
                normalize_phone_number(candidate.phone_number)
                == normalized_phone_number
            ):
                return candidate

        return None

    def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        user = self.get_user(user_id)

        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ResourceConflictError(
                message="User with this email already exists.",
                error_code="user_email_already_exists",
            ) from exc

        self.db.refresh(user)
        return user

    def get_profile(self, user_id: int) -> User:
        return self.get_user(user_id)

    def update_profile(
        self,
        user_id: int,
        profile_data: UserProfileUpdate,
    ) -> User:
        user = self.get_user(user_id)

        for field, value in profile_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> None:
        user = self.get_user(user_id)
        self.db.delete(user)
        self.db.commit()
