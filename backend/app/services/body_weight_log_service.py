from app.core.exceptions import ResourceNotFoundError
from app.models.body_weight_log import BodyWeightLog
from app.schemas.body_weight_log import BodyWeightLogCreate, BodyWeightLogUpdate
from app.services.user_helpers import ensure_user_exists
from sqlalchemy import select
from sqlalchemy.orm import Session


class BodyWeightLogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_body_weight_log(
        self,
        log_data: BodyWeightLogCreate,
    ) -> BodyWeightLog:
        ensure_user_exists(self.db, log_data.user_id)

        body_weight_log = BodyWeightLog(**log_data.model_dump(exclude_none=True))
        self.db.add(body_weight_log)
        self.db.commit()
        self.db.refresh(body_weight_log)
        return body_weight_log

    def list_body_weight_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        user_id: int | None = None,
    ) -> list[BodyWeightLog]:
        statement = select(BodyWeightLog)

        if user_id is not None:
            statement = statement.where(BodyWeightLog.user_id == user_id)

        statement = (
            statement.order_by(BodyWeightLog.logged_at.desc()).offset(skip).limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_body_weight_log(self, log_id: int) -> BodyWeightLog:
        body_weight_log = self.db.get(BodyWeightLog, log_id)

        if body_weight_log is None:
            raise ResourceNotFoundError("Body weight log")

        return body_weight_log

    def update_body_weight_log(
        self,
        log_id: int,
        log_data: BodyWeightLogUpdate,
    ) -> BodyWeightLog:
        body_weight_log = self.get_body_weight_log(log_id)
        updates = log_data.model_dump(exclude_unset=True)

        if "user_id" in updates:
            ensure_user_exists(self.db, updates["user_id"])

        for field, value in updates.items():
            setattr(body_weight_log, field, value)

        self.db.commit()
        self.db.refresh(body_weight_log)
        return body_weight_log

    def delete_body_weight_log(self, log_id: int) -> None:
        body_weight_log = self.get_body_weight_log(log_id)
        self.db.delete(body_weight_log)
        self.db.commit()
