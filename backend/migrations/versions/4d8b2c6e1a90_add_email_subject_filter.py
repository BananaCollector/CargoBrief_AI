"""add persistent email subject filter

Revision ID: 4d8b2c6e1a90
Revises: 2c7e9a1d4b63
Create Date: 2026-11-15 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d8b2c6e1a90"
down_revision: Union[str, None] = "2c7e9a1d4b63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_inbox_filter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("subject_phrase", sa.String(length=200), server_default="", nullable=False),
        sa.CheckConstraint("id = 1", name="ck_email_inbox_filter_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO email_inbox_filter (id, enabled, subject_phrase) "
            "VALUES (1, 0, '')"
        )
    )


def downgrade() -> None:
    op.drop_table("email_inbox_filter")
