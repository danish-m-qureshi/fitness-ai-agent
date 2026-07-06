"""add phase 11 summaries and phase 12 user profile fields

Revision ID: 20260706_0005
Revises: 20260706_0004
Create Date: 2026-07-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260706_0005"
down_revision: Union[str, None] = "20260706_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("phone_number", sa.String(length=50), nullable=True)
    )
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("weight_kg", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("goal_weight_kg", sa.Float(), nullable=True))
    op.add_column(
        "users", sa.Column("activity_level", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users", sa.Column("fitness_goal", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "users", sa.Column("daily_calorie_target", sa.Integer(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("daily_protein_target_g", sa.Float(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "timezone",
            sa.String(length=80),
            server_default="UTC",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_users_phone_number"), "users", ["phone_number"], unique=False
    )

    op.add_column(
        "daily_summaries", sa.Column("total_protein_g", sa.Float(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("total_carbs_g", sa.Float(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("total_fat_g", sa.Float(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("calorie_target", sa.Integer(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("calories_remaining", sa.Integer(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("protein_target_g", sa.Float(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("protein_remaining_g", sa.Float(), nullable=True)
    )
    op.add_column(
        "daily_summaries",
        sa.Column(
            "workouts_completed",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "daily_summaries", sa.Column("latest_weight_kg", sa.Float(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("summary_text", sa.Text(), nullable=True)
    )
    op.add_column(
        "daily_summaries", sa.Column("coaching_suggestions", sa.Text(), nullable=True)
    )
    op.add_column(
        "daily_summaries",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("daily_summaries", "email_sent_at")
    op.drop_column("daily_summaries", "coaching_suggestions")
    op.drop_column("daily_summaries", "summary_text")
    op.drop_column("daily_summaries", "latest_weight_kg")
    op.drop_column("daily_summaries", "workouts_completed")
    op.drop_column("daily_summaries", "protein_remaining_g")
    op.drop_column("daily_summaries", "protein_target_g")
    op.drop_column("daily_summaries", "calories_remaining")
    op.drop_column("daily_summaries", "calorie_target")
    op.drop_column("daily_summaries", "total_fat_g")
    op.drop_column("daily_summaries", "total_carbs_g")
    op.drop_column("daily_summaries", "total_protein_g")

    op.drop_index(op.f("ix_users_phone_number"), table_name="users")
    op.drop_column("users", "timezone")
    op.drop_column("users", "daily_protein_target_g")
    op.drop_column("users", "daily_calorie_target")
    op.drop_column("users", "fitness_goal")
    op.drop_column("users", "activity_level")
    op.drop_column("users", "goal_weight_kg")
    op.drop_column("users", "weight_kg")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "age")
    op.drop_column("users", "phone_number")
