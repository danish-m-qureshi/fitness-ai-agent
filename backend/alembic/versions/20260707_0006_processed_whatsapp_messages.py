"""add processed whatsapp messages table

Revision ID: 20260707_0006
Revises: 20260706_0005
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260707_0006"
down_revision: Union[str, None] = "20260706_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_whatsapp_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("whatsapp_message_id", sa.String(length=255), nullable=False),
        sa.Column("sender_phone_number", sa.String(length=50), nullable=True),
        sa.Column("message_type", sa.String(length=50), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("whatsapp_message_id"),
    )


def downgrade() -> None:
    op.drop_table("processed_whatsapp_messages")
