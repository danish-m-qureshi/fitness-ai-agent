"""add phase 8 meal image analysis fields

Revision ID: 20260705_0003
Revises: 20260705_0002
Create Date: 2026-07-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260705_0003"
down_revision: Union[str, None] = "20260705_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meals",
        sa.Column("image_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "meals",
        sa.Column("analysis_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "meals",
        sa.Column("analysis_raw_response", sa.Text(), nullable=True),
    )
    op.add_column(
        "meals",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meals", "confidence_score")
    op.drop_column("meals", "analysis_raw_response")
    op.drop_column("meals", "analysis_status")
    op.drop_column("meals", "image_path")
