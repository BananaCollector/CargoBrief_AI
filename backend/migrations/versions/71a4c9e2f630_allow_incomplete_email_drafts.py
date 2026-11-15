"""allow incomplete email order drafts

Revision ID: 71a4c9e2f630
Revises: 4d8b2c6e1a90
Create Date: 2026-11-15 17:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "71a4c9e2f630"
down_revision: Union[str, None] = "4d8b2c6e1a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transport_orders") as batch_op:
        batch_op.alter_column(
            "cargo_description",
            existing_type=sa.String(length=200),
            nullable=True,
        )
        batch_op.alter_column(
            "pickup_location",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.alter_column(
            "delivery_location",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    connection = op.get_bind()
    incomplete_count = connection.scalar(
        sa.text(
            "SELECT count(*) FROM transport_orders "
            "WHERE cargo_description IS NULL "
            "OR pickup_location IS NULL "
            "OR delivery_location IS NULL"
        )
    )
    if incomplete_count:
        raise RuntimeError(
            "Cannot downgrade while incomplete email drafts exist; complete or remove them first."
        )
    with op.batch_alter_table("transport_orders") as batch_op:
        batch_op.alter_column(
            "cargo_description",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.alter_column(
            "pickup_location",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "delivery_location",
            existing_type=sa.String(length=255),
            nullable=False,
        )
