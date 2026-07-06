from app.core.exceptions import ResourceNotFoundError
from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.user_helpers import ensure_user_exists
from sqlalchemy import select
from sqlalchemy.orm import Session


class GoalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_goal(self, goal_data: GoalCreate) -> Goal:
        ensure_user_exists(self.db, goal_data.user_id)

        goal = Goal(**goal_data.model_dump())
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def list_goals(
        self,
        skip: int = 0,
        limit: int = 50,
        user_id: int | None = None,
        status: str | None = None,
    ) -> list[Goal]:
        statement = select(Goal)

        if user_id is not None:
            statement = statement.where(Goal.user_id == user_id)

        if status is not None:
            statement = statement.where(Goal.status == status)

        statement = statement.order_by(Goal.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(statement).all())

    def get_goal(self, goal_id: int) -> Goal:
        goal = self.db.get(Goal, goal_id)

        if goal is None:
            raise ResourceNotFoundError("Goal")

        return goal

    def update_goal(self, goal_id: int, goal_data: GoalUpdate) -> Goal:
        goal = self.get_goal(goal_id)
        updates = goal_data.model_dump(exclude_unset=True)

        if "user_id" in updates:
            ensure_user_exists(self.db, updates["user_id"])

        for field, value in updates.items():
            setattr(goal, field, value)

        self.db.commit()
        self.db.refresh(goal)
        return goal

    def delete_goal(self, goal_id: int) -> None:
        goal = self.get_goal(goal_id)
        self.db.delete(goal)
        self.db.commit()
