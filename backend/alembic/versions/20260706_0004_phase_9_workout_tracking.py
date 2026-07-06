"""add phase 9 workout tracking tables

Revision ID: 20260706_0004
Revises: 20260705_0003
Create Date: 2026-07-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260706_0004"
down_revision: Union[str, None] = "20260705_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


exercise_catalogs = sa.table(
    "exercise_catalogs",
    sa.column("name", sa.String),
    sa.column("primary_muscle", sa.String),
    sa.column("secondary_muscles", sa.Text),
    sa.column("equipment", sa.String),
    sa.column("instructions", sa.Text),
)


def upgrade() -> None:
    op.create_table(
        "exercise_catalogs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("primary_muscle", sa.String(length=100), nullable=True),
        sa.Column("secondary_muscles", sa.Text(), nullable=True),
        sa.Column("equipment", sa.String(length=100), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exercise_catalogs_name"),
        "exercise_catalogs",
        ["name"],
        unique=True,
    )

    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workout_sessions_user_id"),
        "workout_sessions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workout_session_id", sa.Integer(), nullable=False),
        sa.Column("exercise_catalog_id", sa.Integer(), nullable=True),
        sa.Column("exercise_name", sa.String(length=150), nullable=False),
        sa.Column("muscle_group", sa.String(length=100), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["exercise_catalog_id"],
            ["exercise_catalogs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workout_session_id"],
            ["workout_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workout_exercises_exercise_catalog_id"),
        "workout_exercises",
        ["exercise_catalog_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workout_exercises_workout_session_id"),
        "workout_exercises",
        ["workout_session_id"],
        unique=False,
    )

    op.create_table(
        "exercise_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workout_exercise_id", sa.Integer(), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.Column("is_warmup", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workout_exercise_id"],
            ["workout_exercises.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exercise_sets_workout_exercise_id"),
        "exercise_sets",
        ["workout_exercise_id"],
        unique=False,
    )

    op.bulk_insert(
        exercise_catalogs,
        [
            {
                "name": "bench press",
                "primary_muscle": "chest",
                "secondary_muscles": "triceps, shoulders",
                "equipment": "barbell",
                "instructions": "Press a barbell from chest level while lying on a bench.",
            },
            {
                "name": "squat",
                "primary_muscle": "quads",
                "secondary_muscles": "glutes, hamstrings, core",
                "equipment": "barbell",
                "instructions": "Squat with controlled depth and a braced torso.",
            },
            {
                "name": "deadlift",
                "primary_muscle": "posterior chain",
                "secondary_muscles": "back, glutes, hamstrings",
                "equipment": "barbell",
                "instructions": "Lift the bar from the floor with a neutral spine.",
            },
            {
                "name": "overhead press",
                "primary_muscle": "shoulders",
                "secondary_muscles": "triceps, upper chest",
                "equipment": "barbell",
                "instructions": "Press the bar overhead from shoulder height.",
            },
            {
                "name": "pull-up",
                "primary_muscle": "back",
                "secondary_muscles": "biceps, rear delts",
                "equipment": "pull-up bar",
                "instructions": "Pull your body upward until the chin clears the bar.",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_exercise_sets_workout_exercise_id"),
        table_name="exercise_sets",
    )
    op.drop_table("exercise_sets")
    op.drop_index(
        op.f("ix_workout_exercises_workout_session_id"),
        table_name="workout_exercises",
    )
    op.drop_index(
        op.f("ix_workout_exercises_exercise_catalog_id"),
        table_name="workout_exercises",
    )
    op.drop_table("workout_exercises")
    op.drop_index(
        op.f("ix_workout_sessions_user_id"),
        table_name="workout_sessions",
    )
    op.drop_table("workout_sessions")
    op.drop_index(op.f("ix_exercise_catalogs_name"), table_name="exercise_catalogs")
    op.drop_table("exercise_catalogs")
